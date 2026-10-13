# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **`desktop_perceive` 新增 `capture_id` 防呆点击：`desktop_mouse` / `desktop_mouse_drag` 可用 `capture_id + element_id` 引用登记的元素中心。** 屏幕空间 perceive 运行登记进进程级 FIFO 注册表（保留最近 8 次，uuid v4），鼠标工具把 id 对解析成服务端登记的屏幕坐标后再作用；与裸 x/y 混用、只传一半、id 过期均得带恢复指引的明确报错，杜绝「图片坐标当屏幕坐标」类失误。裸 x/y 保留为旧接口。新增 4 项单测（注册解析 / 未知 id / 未知元素 / FIFO 逐出）。
- **新增 `scripts/schema_drift_check.py`：本仓库与 Nuphus 主项目工具 schema 的结构性漂移检查。** 工具名 / required / 属性名视为契约逐项比对（描述措辞允许有意分叉；产品级分叉进白名单且逐条带理由）。当前 44 个共享工具零结构漂移；该检查也挖出了本次放开的四向滚动等真实能力分叉。

### Changed

- **Windows 执行 HUD 有了品牌标识，并改为实色卡片 + 三行结构。** 右下角状态胶囊从半透明两行（主文 + mono 次行）重做为**实色不透明三行**：`Nuphus MCP` 品牌眉标（10px 弱灰）钉在主文上方，与工具名（13.5px）、mono 次行（11px）共用左对齐轴线；卡片 alpha 217 → 255，不再叠桌面，小字不再发虚。品牌做眉标而非右侧浮动字标——与主文/次行同轴，不破坏两行信息的层级。相位图标随卡片放大到 18px，几何与描边同步重算。macOS/Linux 系统通知标题本就是 `nuphus-mcp`，此番后三端皆有品牌。新增 `cargo run -p desktop-api --example hud_preview`：依次预览执行中 / 完成 / 失败三态，供样式迭代肉眼验收。
- **`desktop_vision` 失败文案升级为分类诊断（auth / billing / rate_limit / image_too_large / other 五类）。** 文案写明失败原因与出路（计费 → 到服务商控制台充值，限流 → 稍等重试，密钥 → 检查 `NUPHUS_MCP_VISION_API_KEY`）；计费关键词（余额不足 / 配额耗尽 / insufficient_quota …）优先于 HTTP 429 判定，OpenAI 风格 `insufficient_quota` 的 429 响应被正确归为计费而非可重试限流；文案内嵌判别短语，分类器往返防劫持（敌意 body 单测覆盖）。
- **`browser_extract` 重写：噪声子树预移除 + 五级主内容选择器 + 非空命中降级。** 读取前移除 nav / aside / footer / script / style / noscript / svg；选择器由四级升为五级（新增 `[role=main]`、`[itemprop=mainContent]`）；首个**非空**命中生效——修复「命中 `<article>` 但为空 SPA 骨架 → 返回无内容」的真实 bug。工具描述同步与实现对齐，不再声称未实现的「strips nav/ads」。
- **滚动放开四方向：`desktop_mouse` 的 scroll 支持 `left` / `right`**（Win32 `MOUSEEVENTF_HWHEEL`，自主项目 desktop-api 移植）**，`browser_scroll` schema 同步放开 CDP 层本已实现的四方向**；负数滚动量现明确报错。此前 schema 把已实现能力锁死在两方向。
- **`browser_screenshot` 双模式：`path` 省略时返回 base64 data URI 供内联读图**（client 层早有该回退，执行器此前人为拒绝空 path）；**`desktop_input` 的 `hwnd` 改为可选**，省略时作用于当前前台窗口（运行时行为早已存在，schema 必填约束与之自相矛盾）；`desktop_mouse_drag` 的 required 相应清空（捕获对 / 裸坐标按端点二选一）。

## [0.3.2] - 2026-10-11

### Fixed

- **`browser_snapshot` no longer drops iframes: nested frames are collected, unreadable ones are disclosed.** The snapshot used to read only the main document's AX tree, so headings, inputs and buttons inside iframes never appeared — and the result still looked like a complete page. On pages whose main interaction lives in an iframe (payment callbacks, OAuth flows, relay dashboards) the agent silently got a crippled view (`browser_evaluate` reaching the same content through `window.frames` made the gap even harder to notice). Now: `Page.getFrameTree` enumerates every frame, and each session-reachable child frame is collected with its own `frameId`; main-document refs keep their original numbering and come first, nested-frame refs follow under a `── 嵌套 frame：… ──` header naming their frame, and `@N` resolution in click / type / exec routes by frame ownership (clicking an `@N` inside an iframe lands in the child document — verified by a live test). Frames that cannot be read (cross-process / cross-origin sandboxes, empty AX trees, over cap) are listed one by one in a trailing `⚠ … 未包含在上方快照中` disclosure, so a partial view is always explicit; if frame-tree enumeration itself fails, the snapshot degrades to the previous main-document-only behavior instead of failing.

## [0.3.1] - 2026-09-29

### Fixed

- **The server no longer dies mid-tool on its deepest path.** `browser_navigate`
  runs the stdio loop + tool dispatch on the main thread with the default stack,
  and that path (navigate → CDP client → per-command timeouts → nested
  chromiumoxide futures) overflowed it: the process exited with
  `thread 'main' has overflowed its stack`, after which every `tools/call` went
  unanswered until the process was killed — with the spawned Chrome left holding
  the debug port. The loop now runs on a dedicated thread with a 64 MB stack.
- **A dead CDP connection is no longer silent.** The handler task used to swallow
  its own exit, so a browser that went away left no trace and the only symptom was
  a run of tool calls that "hang". It now logs how it ended (error vs. clean
  close), which separates "the browser died" from "the page is busy".
- **Unbounded waits are bounded** with readable errors — the shared browser
  client lock and the process-level automation lock (both acquired outside every
  per-tool budget, so either could wedge the whole server), the headless probe in
  `instance_is_headless`, `Browser.close` / child `wait` in `close()`, and page
  creation in `new_tab` / `get_or_create_page`.
- **`browser_press` verifies its effect** like `browser_click` / `browser_type`
  already did. A key that changes nothing within 2s now returns a note instead of
  a silent "Pressed Enter". This also makes the focus trap visible: while a tab
  is not the focused/visible one, CDP input is dropped (`document.hasFocus()` is
  false) and nothing happens at all; the note points at `browser_switch_tab` /
  `browser_new_tab`.

### Changed

- `kill_chrome_for_profile` waits with an async sleep instead of blocking a
  runtime worker for 800ms.

## [0.3.0] - 2026-09-26

### Added

- **Semantic desktop tool family — 7 new tools** — Accessibility/UIA-first control
  sharing one contract: **observe → pick a `candidate_id` → execute → verify**.
  `desktop_targets_list`, `desktop_target_bind`, `desktop_semantic_observe`,
  `desktop_semantic_candidate`, `desktop_semantic_execute`,
  `desktop_semantic_action`, `desktop_verify_state`. Native window handles,
  coordinates and platform locators never cross the MCP boundary — callers only
  ever see opaque ids and stable semantic locators.
- **macOS Accessibility (AX) support** for the semantic family alongside the
  Windows UIA backend — implemented with `std` and hand-written FFI bindings, so
  no new dependencies are introduced.
- **`desktop_perceive` gains a `region` argument** — analyse a cropped screen area
  instead of the whole desktop; results now carry a `coordinate_space` field and
  screen-space coordinates. `path` and `region` are mutually exclusive.

### Changed

- **Screenshot geometry is validated** — a geometry sample is taken before and
  after the capture and the frame is rejected when the two disagree, so returned
  coordinates always describe the frame actually produced. Window/client-area
  scopes report no geometry instead of guessing an origin they cannot know.
- **Chrome launch failures are classified** — sandbox and enterprise-policy
  markers are recognised from Chrome's stderr and surfaced as actionable
  messages instead of a raw stderr tail.

### Fixed

- **`yolo.rs`**: `erasing_op` (`0 * h * w`, always zero) and `needless_range_loop`.
- **`client.rs`**: unnecessary `unwrap`; `match` → `unwrap_or_default`.
- **UIA live-test fixture** — the fixture script is resolved by searching ancestor
  directories, so the live tests also run in the standalone repository layout.
- **Build script: the ONNX Runtime package download no longer restarts from zero** —
  transfers resume (`curl -C -`), the per-attempt timeout is raised to 30 minutes,
  and a partial archive is kept instead of deleted when verification fails. Any
  interrupted transfer used to discard the whole 129 MB package (so every build
  re-downloaded it), and a truncated-yet-large cache was then reused forever
  without ever extracting a library.

## [0.2.3] - 2026-09-17

### Changed

- **执行 HUD 视觉重构**：Windows 端由「右下角黑色文字浮条」改为与主项目 HUD 同源的直角状态卡片
  —— 3px 相位色条 + 14px 相位图标（转圈 / 对勾 / 感叹号）+ 12.5px 主文与 10px mono 次行
  + 执行中底部 2px 渐变扫光 + 相位色辉光描边。不再出现类似「告警条 / 全宽横幅」的形态。
- **HUD 锚点改用工作区**：以 `SPI_GETWORKAREA` 取主显示器工作区右下角定位，避免与任务栏 /
  托盘区重叠（原先按整屏定位会压住任务栏）。
- **状态图标改由 HUD 自绘**：Agent 侧不再拼接 `▶ ✓ ⚠ ✗` 字形；`HudKind` 新增 `Fail`
  变体（失败态使用 error 相位色），macOS / Linux 的完成态通知行为不变。

## [0.2.2] - 2026-08-30

### Changed

- **Compacted 17 MCP tool descriptions to short phrases** — key parameters,
  hard constraints, and behavior contracts preserved, reducing prompt-injection
  overhead for AI clients.

## [0.2.1] - 2026-08-29

### Added

- **Cross-platform system notifications for the execution HUD** — macOS
  `osascript` / Linux `notify-send`, so tool-call progress stays visible even
  when the terminal is not focused.

## [0.2.0] - 2026-08-29

### Added

- **Execution HUD**: non-intrusive floating status bar showing tool-call
  execution in real time (fades out automatically).

### Fixed

- **HUD disappearing permanently after one show** — the floating bar now stays
  until the next tool call; minimized-window activation now restores and
  focuses the window.
- **Browser**: upgrade a resident headless Chrome instance to headed mode when
  a headed request arrives.
- **CI**: EOF newline on `mouse.rs`, bump `h2` for RUSTSEC-2026-0258.

## [0.1.13] - 2026-08-21

### Added

- **`browser_press` — real key dispatch** — a new tool that sends physical key
  events (named keys, single characters and chords such as `Control+c`) to the
  focused element through CDP `Input.dispatchKeyEvent`; `snapshot` controls
  whether a post-press page snapshot is attached.
  ([#6](https://github.com/mrpulor-gh/nuphus-mcp/pull/6) by
  [@Steooenwolf-666](https://github.com/Steooenwolf-666))

### Fixed

- **Mouse movement silently "succeeding" without moving the cursor** — `move_to`
  on Windows ignored the `SetCursorPos` return value (`let _ = ...`) and always
  returned `Ok`, so when the OS rejected the move (session / privilege limits)
  callers got a fake success while the cursor never moved. `move_to` now checks
  the API result and verifies the actual cursor position against the target
  (2px tolerance for DPI rounding) before returning; any mismatch fails loudly
  with a descriptive error instead of a silent success. `drag` propagates the
  same errors instead of swallowing them mid-path.

## [0.1.12] - 2026-08-17

### Added

- **Native file drag onto page elements** — `browser_drag_files` drives the
  browser's own drag pipeline with real file payloads (CDP
  `Input.dispatchDragEvent`), so drops land on targets that have no
  `input[type=file]`; paths must exist and are canonicalized before dispatch.
  ([#4](https://github.com/mrpulor-gh/nuphus-mcp/pull/4) by
  [@Steooenwolf-666](https://github.com/Steooenwolf-666))
- **Mouse button selection for browser clicks** — `browser_click` gains a
  `button` argument (`left` / `right` / `middle`); right and middle clicks always
  dispatch real CDP mouse events, and the button mask is carried through the
  press and cleared on release.
  ([#4](https://github.com/mrpulor-gh/nuphus-mcp/pull/4) by
  [@Steooenwolf-666](https://github.com/Steooenwolf-666))

### Changed

- **Tool schemas, runtime checks and docs aligned** — write-tool classification
  is now a single source of truth shared by the runtime guard and the schema
  declaration, so the two cannot drift apart; the affected tool schemas and both
  `TOOLS.md` references were updated to match.
  ([#5](https://github.com/mrpulor-gh/nuphus-mcp/pull/5) by
  [@Steooenwolf-666](https://github.com/Steooenwolf-666))

## [0.1.11] - 2026-08-09

### Fixed

- **npm install on macOS** — the `@nuphus/nuphus-mcp-osx-arm64` platform
  package declared `"os": ["osx"]`, which never matches npm's
  `process.platform` value on macOS (`"darwin"`), so the optional dependency
  was skipped with a `notsup` warning and the postinstall check failed. The
  generated `os` field now uses npm's platform name `"darwin"` (the package
  name stays `osx-arm64`); the win32/linux packages were already correct.
  ([#3](https://github.com/mrpulor-gh/nuphus-mcp/pull/3) by
  [@yyyyyyyyiiiii](https://github.com/yyyyyyyyiiiii))

## [0.1.10] - 2026-08-07

### Added

- **Anthropic native vision backend** — `desktop_vision` can now talk to Claude
  (and any Anthropic Messages API endpoint) natively. Set `NUPHUS_MCP_VISION_PROVIDER`
  to `auto` (default), `openai`, or `anthropic`. In `auto` mode the provider is
  inferred from the base URL: an endpoint whose host contains `anthropic` is sent
  the native `/v1/messages` protocol with `x-api-key` + `anthropic-version:
  2023-06-01` headers and a real `image`/`source` base64 block; everything else
  keeps the OpenAI-compatible `image_url` path. (Anthropic's OpenAI-compat layer
  does not convert `image_url` blocks, so Claude requires the native protocol —
  merely pointing a base URL at `api.anthropic.com` used to fail or silently drop
  the image.)
- **Configurable vision `max_tokens`** — new `NUPHUS_MCP_VISION_MAX_TOKENS` env var
  (default **1024**, validated `1..=32768`). Previously hardcoded, the value is the
  request parameter that Chinese OpenAI-compatible vision models (Zhipu GLM-4V-Flash
  et al.) cap at 1024 — exceeding it returns HTTP 400. Defaulting to 1024 makes
  BYOK vision work against all those providers out of the box.

### Fixed

- **Unified CDP timeouts** — every CDP call now runs under a single 5-second budget
  through one `cdp()` wrapper. The old per-command hardcoded 30s could make a
  half-dead page hang `snapshot`/`click` for 15s+ before erroring; those now
  fast-fail in ~5s with actionable errors. A connection error on `snapshot` no
  longer silently falls back to a JS eval that reports a false "empty page", and a
  reconnect race can no longer kill a live browser while trying to verify one.

## [0.1.9] - 2026-08-06

### Added

- **YOLO model auto-download** — `desktop_perceive` now downloads
  `icon_detect.onnx` together with the PaddleOCR models on first run, instead
  of requiring a manual placement. Default source is onnx-community's
  OmniParser icon_detect 640x640 ONNX export (hf-mirror.com first,
  huggingface.co fallback; same `[1,3,640,640]` → `[1,5,8400]` I/O contract as
  the exported model). Set `NUPHUS_MCP_YOLO_MODEL_URL` to override with any
  direct `.onnx` URL (e.g. the full ~80 MB OmniParser export or a private
  mirror). A failed YOLO download degrades gracefully to OCR-only and reports
  `yolo_available: false` — it never blocks perceive. `NUPHUS_MCP_NO_MODEL_DOWNLOAD=1`
  skips both OCR and YOLO downloads. `icon_detect.onnx` passes the same size
  floor and ONNX trial-load integrity checks as the OCR models.

### Fixed

- **`NUPHUS_MCP_YOLO_MODEL_URL` was documented but unimplemented** — the env
  var is now actually honored by the downloader.

## [0.1.8] - 2026-08-06

### Added

- **External browser self-healing** — attach to a fingerprint browser now
  survives window reopens: set `NUPHUS_BROWSER_EXE_PATH` (plus optional
  `NUPHUS_BROWSER_NAME` / `NUPHUS_BROWSER_USER_DATA_DIR`) alongside
  `NUPHUS_MCP_BROWSER_CDP_URL`, and when the configured endpoint stops
  answering the server locates the window process by exe path, re-resolves
  its live debug port (literal cmdline port, or `DevToolsActivePort` for
  random-port launches), verifies it with a `no_proxy` CDP probe and retries
  once. Attach failures remain hard errors with actionable, user-facing
  guidance — still no silent fallback into a managed Chrome.
- **Trusted click mode** — `browser_click` gains an optional `trusted`
  parameter (default `false`). When `true`, the click is dispatched as real
  CDP `Input.dispatchMouseEvent` events (`isTrusted=true`, produces user
  activation) instead of a JS-synthesized `el.click()` — required to unlock
  autoplay-gated audio/video playback and other gesture-gated features.
  Default JS click behavior is unchanged.
- **External browser support** — set `NUPHUS_MCP_BROWSER_CDP_URL` (e.g.
  `http://127.0.0.1:9222`) to attach all `browser_*` tools to a user-started
  external browser (anti-detect / fingerprint browsers) instead of launching a
  managed Chrome. Attach failures are hard errors (no silent fallback); the
  external instance is never killed on exit. Endpoint discovery bypasses the
  system proxy (`no_proxy`).

## [0.1.7] - 2026-08-04

### Fixed

- **Internal mechanism audit remediation** — full audit of server core, CDP
  client, desktop automation and release pipeline; all P1/P2 findings fixed:
- **Server**: tool execution is now isolated via `tokio::spawn` — a panicking
  tool returns `isError` instead of killing the whole server process;
  initialize no longer echoes the client's protocol version; JSON-RPC
  validation (-32600/-32700/-32602, explicit `id:null`); `shutdown`/`exit`
  implemented; `desktop_*` dispatch/schema drift guard.
- **Automation lock**: token-based ownership, atomic publish (tmp+hard_link),
  heartbeat renewal (long-running tools no longer outlive the 90s TTL and
  break cross-process mutual exclusion), rename-before-delete (TOCTOU fix).
- **Browser**: structured `BrowserError::Connection` classification — page JS
  exceptions can no longer trigger a reconnect that kills a healthy browser;
  timeout path now checks the child process is actually dead before
  reconnect-kill; retries limited to read-only tools (write tools report
  "may have been executed" instead of silently re-executing); download
  directory re-configured after reconnect; JS interpolation uniformly
  escaped; `batch_exec` reports honest `unknown` status; snapshot refs
  invalidated on page/target changes; navigation URL host filter blocks
  link-local/private ranges (`NUPHUS_MCP_ALLOW_PRIVATE_NAV=1` escape hatch).
- **Desktop**: clipboard read no longer dereferences an unlocked HGLOBAL
  with an unbounded scan (UB fix); foreground activation is verified before
  input injection; ONNX sessions are process-level singletons (no more
  80MB model reload per perceive call); temp capture files are cleaned up;
  model downloads use per-PID partial files and an ORT load check;
  middle-click support; ort dylib path guard against stale System32 DLL.
- **Release pipeline**: Cargo.toml version aligned with npm (0.1.0 → real
  version — published binaries reported the wrong `serverInfo.version`);
  `verify-release-versions.js` preflight gate (tag ↔ npm ↔ Cargo.toml must
  match); E409 publish handling now verifies via `npm view` instead of
  blanket success; CI covers all three crates plus real-Chrome integration
  tests and advisory `cargo audit`; npm CLI validates platform-package
  version; local publish guard against stale binaries.

## [0.1.6] - 2026-08-04

### Fixed

- **Browser dispatch regression (P1, release-blocking)**: the connection
  self-healing refactor (0.1.5) dropped five dispatch arms from
  `browser.rs` while leaving the tools in `tools/list` — `browser_close`,
  `browser_cookies_get`, `browser_cookies_set`, `browser_import_cookies`,
  and `browser_upload` (registered as `browser_upload_file`, so `browser_upload`
  fell through to "Unknown browser tool"). Affected every 0.1.5 npm binary.
  All five arms restored and `browser_upload` renamed to match the schema.
- **Regression guard**: new `dispatch_matches_schema` test asserts that every
  `browser_*` tool registered in `schemas::all_tools` has a dispatch branch
  (enforced by `EXECUTABLE_BROWSER_TOOLS`), so a future schema/dispatch drift
  fails CI instead of surfacing at runtime.
- **npm platform package scope (release-blocking)**: `gen-platform-packages.js`
  generated unscoped names (`nuphus-mcp-win32-x64`) while the registry packages
  are `@nuphus/nuphus-mcp-*`. Publishing the unscoped name made npm treat each
  platform package as brand-new and return 403 spam detection — the 0.1.5 CI
  publish failed for this reason. Script now emits the scoped name (directory
  layout unchanged), and 0.1.6 was published from the corrected packages.

## [0.1.5] - 2026-08-04

### Added

- **Connection-level self-healing (browser)**: a dead CDP connection (killed /
  crashed Chrome) is automatically detected at the operation level, the browser
  is relaunched, and the operation retried once — a mid-workflow browser death
  no longer turns into a string of user-visible errors. `launch()`'s liveness
  probe deliberately does NOT diagnose death (a probe timeout is not proof of
  death); death is proven only by a connection-class error from a real
  operation.

## [0.1.4] - 2026-08-04

### Fixed

- **Anti-detection fingerprints triggering CAPTCHA walls**: Chrome no longer
  exposes the CDP automation state — `--disable-blink-features=AutomationControlled`
  plus an injected `navigator.webdriver` hider on every page, removing the
  single most flaggable signature of automation for user-authorized workflows.

## [0.1.3] - 2026-08-03

### Fixed

- **Strict confirm mode deadlocked with spec-compliant clients**: `confirm` was
  not declared in write-tool input schemas, so spec-compliant MCP clients
  stripped it before the server ever saw it and strict-confirm mode could never
  be satisfied. `confirm` is now declared on every tool the runtime may
  classify as a write, derived from the same source of truth as the runtime
  check (guarded by anti-drift tests).

### Docs

- Added Gitee mirror links to the READMEs.

## [0.1.2] - 2026-08-02

### Fixed

- **CDP liveness probe killing open pages**: the probe used `Target.getTargets`,
  whose response handler re-creates every target and drops their PageHandles —
  any operation after the first failed with "receiver is gone" while the probe
  still reported "alive". The probe is now the side-effect-free `version()`.
- **Navigate hanging 30s on slow pages**: `goto` waits for the `load` lifecycle
  event, which a page with hanging subresources never fires. Navigation is now
  bounded and degrades to polling `document.readyState` (DOM usable at
  "interactive") instead of hanging the tool on the hard CDP timeout.

## [0.1.1] - 2026-08-02

### Added

- **Cross-process automation lock**: desktop and browser automation operate on
  exclusive machine resources; multiple nuphus-mcp instances (one per Agent)
  coordinate through a shared lock file with busy rejection and TTL-based crash
  self-healing.

### Fixed

- **npm launcher**: resolve the nested `optionalDependencies` layout — npm >= 10
  nests platform packages under the dependent package in global installs
  instead of hoisting them as siblings; the launcher now walks up the directory
  tree like `require` does.
- **CI**: platform-aware path tests and workspace-wide `cargo fmt`.

## [0.1.0] - 2026-07-31

### Added

- Initial public release of `nuphus-mcp`, an MCP Server exposing desktop and
  browser automation over stdio (JSON-RPC 2.0).
- **Desktop automation (15 tools)**: `desktop_screen_size`, `desktop_screenshot`,
  `desktop_windows_list`, `desktop_window_activate`, `desktop_window_screenshot`,
  `desktop_window_move`, `desktop_window_resize`, `desktop_window_info`,
  `desktop_vision`, `desktop_perceive`, `desktop_mouse`, `desktop_mouse_drag`,
  `desktop_input`, `desktop_clipboard_clean`, `desktop_clipboard_write`.
- **Browser automation (21 tools)**: `browser_navigate`, `browser_snapshot`,
  `browser_exec`, `browser_click`, `browser_type`, `browser_scroll`,
  `browser_extract`, `browser_screenshot`, `browser_close`, `browser_evaluate`,
  `browser_back`, `browser_forward`, `browser_wait_for`, `browser_cookies_get`,
  `browser_cookies_set`, `browser_import_cookies`, `browser_upload`,
  `browser_list_downloads`, `browser_new_tab`, `browser_list_tabs`,
  `browser_switch_tab`.
- **Protocol**: JSON-RPC 2.0 over stdio; `initialize` / `notifications/initialized`
  / `ping` / `tools/list` / `tools/call`; protocol version `2024-11-05`.
- **Safety**:
  - MCP `annotations`: 25 write tools marked `destructiveHint`, 11 read tools
    marked `readOnlyHint`.
  - Strict confirm mode (`--confirm-write` / `NUPHUS_MCP_CONFIRM_WRITE=1`)
    requires explicit `"confirm": true` on write tools.
  - Screenshot path validation (path traversal / protected directories) and
    upload file existence check.
- **Workspace**: three crates — `nuphus-mcp` (server), `nuphus-browser`
  (CDP browser core, chromiumoxide), `desktop-api` (desktop control core,
  vendored, xcap + Win32).
- **Docs**: `TOOLS.md` / `TOOLS.zh-CN.md` (36-tool reference), demo example
  (`examples/demo.rs`).

[0.1.9]: https://github.com/mrpulor-gh/nuphus-mcp/releases/tag/v0.1.9
[0.1.8]: https://github.com/mrpulor-gh/nuphus-mcp/releases/tag/v0.1.8
[0.1.7]: https://github.com/mrpulor-gh/nuphus-mcp/releases/tag/v0.1.7
[0.1.6]: https://github.com/mrpulor-gh/nuphus-mcp/releases/tag/v0.1.6
[0.1.5]: https://github.com/mrpulor-gh/nuphus-mcp/releases/tag/v0.1.5
[0.1.4]: https://github.com/mrpulor-gh/nuphus-mcp/releases/tag/v0.1.4
[0.1.3]: https://github.com/mrpulor-gh/nuphus-mcp/releases/tag/v0.1.3
[0.1.2]: https://github.com/mrpulor-gh/nuphus-mcp/releases/tag/v0.1.2
[0.1.1]: https://github.com/mrpulor-gh/nuphus-mcp/releases/tag/v0.1.1
[0.1.0]: https://github.com/mrpulor-gh/nuphus-mcp/releases/tag/v0.1.0