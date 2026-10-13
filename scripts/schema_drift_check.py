# schema_drift_check.py — compare nuphus-mcp tool schemas against the Nuphus main app.
#
# nuphus-mcp's crates/nuphus-mcp/src/tools/schemas.rs hand-mirrors the main
# app's src/tools/desktop_schemas.rs. Descriptions are ALLOWED to diverge (the
# two products intentionally phrase guidance differently), but STRUCTURE must
# not drift: tool sets, required arrays and property names are contracts.
#
# Checks per shared tool name:
#   1. required[] sets match
#   2. property-name sets match (new properties must appear on both sides)
#
# Differences listed in INTENTIONAL_DIVERGENCE are skipped (product-level forks
# with a recorded reason); everything else exits 1 with a printed diff.
#
# Usage:  python scripts/schema_drift_check.py [--main <Nuphus repo root>]
# Default main-repo root: ..\Nuphus (sibling checkout).

import json
import os
import re
import sys
from pathlib import Path

MCP_SCHEMA = Path(__file__).resolve().parent.parent / "crates" / "nuphus-mcp" / "src" / "tools" / "schemas.rs"
DEFAULT_MAIN = Path(__file__).resolve().parent.parent.parent / "Nuphus"
MAIN_SCHEMA = "src/tools/desktop_schemas.rs"

TOOL_DEF_RE = re.compile(
    r'tool_def(?:_with_selector_or_ref)?\(\s*"([a-z_0-9]+)"\s*,', re.S
)


def src(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def balanced_paren_slice(text: str, start: int) -> str:
    """Return the tool_def(...) argument text starting at `start` (index of `tool_def`).

    String-aware and bracket-aware: skips over string bodies (with backslash
    escapes) and tracks (), [] and {} nesting so array literals survive.
    """
    i = text.index("(", start)
    depth = 0
    in_str = False
    j = i
    while j < len(text):
        c = text[j]
        if in_str:
            if c == "\\":
                j += 2
                continue
            if c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c in "([{":
                depth += 1
            elif c in ")]}":
                depth -= 1
                if depth == 0:
                    return text[i + 1 : j]
        j += 1
    raise ValueError(f"unbalanced parens from index {start}")


def split_top_level_commas(args: str):
    """Split a Rust argument list on top-level commas (respect nesting of (), [], {}, strings)."""
    parts, buf, depth, i, in_str = [], [], 0, 0, False
    while i < len(args):
        c = args[i]
        if in_str:
            if c == "\\":
                buf.append(args[i : i + 2])
                i += 2
                continue
            if c == '"':
                in_str = False
            buf.append(c)
        else:
            if c == '"':
                in_str = True
                buf.append(c)
            elif c in "([{":
                depth += 1
                buf.append(c)
            elif c in ")]}":
                depth -= 1
                buf.append(c)
            elif c == "," and depth == 0:
                parts.append("".join(buf).strip())
                buf = []
            else:
                buf.append(c)
        i += 1
    if buf:
        parts.append("".join(buf).strip())
    return parts


PROPS_RE = re.compile(r"json_props!\s*\{(.*)\}\s*,?\s*$", re.S)
PROP_KEY_RE = re.compile(r'"([A-Za-z_0-9]+)"\s*=>', re.S)
REQUIRED_RE = re.compile(r"&\[((?:\s*\"[^\"]*\"\s*,?\s*)*)\]")
REQUIRED_ITEM_RE = re.compile(r'"([^"]+)"')

EMPTY_PROPS_TOKENS = {"json!({})", "serde_json::json!({})"}

# Recorded product-level forks. Structure here is ALLOWED to differ; every
# entry must carry a reason so future audits can re-judge.
INTENTIONAL_DIVERGENCE = {
    # nuphus-mcp executes its own independent server (no workflow engine), so
    # the main app's workflow-replay locator/launch-ref params don't exist here.
    "desktop_input": {"props"},
    # Main app's mouse schema carries hwnd (scoped automation via its desktop
    # client); the MCP server serializes everything through machine-wide
    # automation locks instead, so it has no hwnd parameter.
    "desktop_mouse": {"props"},
    # The two vision paths evolved different parameter names AND optionality:
    # nuphus-mcp accepts a path OR captures the screen itself (path optional,
    # region cropping supported), the main app requires image_path.
    "desktop_vision": {"required", "props"},
    "desktop_perceive": {"required", "props"},
    # PARSER BLIND SPOT (not real drift): the main app injects delivery_mode /
    # tree_cursor / amount / checked / direction / completion_policy /
    # expectation into these tools programmatically AFTER the tool_def calls
    # (desktop_schemas.rs loops over the declared schemas); this script only
    # reads literal tool_def arguments, so those props are invisible on the
    # main side. mcp declares them inline — same effective schema.
    "desktop_semantic_observe": {"props"},
    "desktop_semantic_execute": {"props"},
    "desktop_semantic_action": {"props"},
    "desktop_target_bind": {"props"},
    # TRUE PRODUCT FORK: main nests verification params inside the expectation
    # object only; mcp additionally keeps legacy flat top-level params
    # (condition/expected/locator/value/timeout_ms/stable_samples) for LLM
    # ergonomics. Both validate the same expectation contract.
    "desktop_verify_state": {"props"},
}


def parse_tool_def(text: str, start: int):
    """Parse one tool_def(...) → (name, {required, props}) or None if malformed."""
    m = TOOL_DEF_RE.match(text, start)
    if not m:
        return None
    name = m.group(1)
    body = balanced_paren_slice(text, m.start())
    parts = split_top_level_commas(body)
    if len(parts) < 4:
        return None
    props_arg, required_arg = parts[2], parts[3]
    props = set()
    pm = PROPS_RE.search(props_arg)
    if pm:
        props = set(PROP_KEY_RE.findall(pm.group(1)))
    elif props_arg.strip() in EMPTY_PROPS_TOKENS:
        props = set()
    rm = REQUIRED_RE.search(required_arg)
    required = set(REQUIRED_ITEM_RE.findall(rm.group(1))) if rm else set()
    return name, {"required": required, "props": props}


def parse_tools(text: str) -> dict:
    tools = {}
    for m in TOOL_DEF_RE.finditer(text):
        parsed = parse_tool_def(text, m.start())
        if parsed:
            name, data = parsed
            tools[name] = data
    return tools


def main() -> int:
    argv = sys.argv[1:]
    main_root = DEFAULT_MAIN
    if "--main" in argv:
        main_root = Path(argv[argv.index("--main") + 1])

    mcp_text = src(MCP_SCHEMA)
    main_text = src(main_root / MAIN_SCHEMA)

    mcp_tools = parse_tools(mcp_text)
    main_tools = parse_tools(main_text)
    # The main side also declares tools the MCP server does not execute; compare
    # on shared names, report one-sided names as information (not drift).
    shared = sorted(set(mcp_tools) & set(main_tools))
    only_mcp = sorted(set(mcp_tools) - set(main_tools))
    only_main = sorted(set(main_tools) - set(mcp_tools))

    problems = []
    for name in shared:
        mcp, main = mcp_tools[name], main_tools[name]
        skip = INTENTIONAL_DIVERGENCE.get(name, set())
        if "required" not in skip and mcp["required"] != main["required"]:
            problems.append(
                f"{name}: required drift\n  mcp : {sorted(mcp['required'])}\n  main: {sorted(main['required'])}"
            )
        if "props" not in skip and mcp["props"] != main["props"]:
            problems.append(
                f"{name}: property drift\n  mcp only : {sorted(mcp['props'] - main['props'])}\n  main only: {sorted(main['props'] - mcp['props'])}"
            )

    print(f"shared tools compared: {len(shared)}")
    if only_mcp:
        print(f"only in nuphus-mcp (informational): {only_mcp}")
    if only_main:
        print(f"only in main app (informational): {only_main}")
    if problems:
        print(f"\nSTRUCTURAL DRIFT ({len(problems)}):")
        for p in problems:
            print(" -", p)
        return 1
    print("no structural drift")
    return 0


if __name__ == "__main__":
    sys.exit(main())
