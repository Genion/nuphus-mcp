//! HUD 样式预览（仅 Windows 胶囊有意义；macOS/Linux 走系统通知，仅完成态）。
//!
//! 用法：`cargo run -p desktop-api --example hud_preview`
//! 依次展示 执行中 → 完成 → 失败 三态，每态停留数秒，供样式迭代时肉眼验收。

use desktop_api::hud::{show, HudKind};
use std::thread::sleep;
use std::time::Duration;

fn main() {
    show(
        HudKind::Start,
        "desktop_window_activate hwnd=262896",
        30_000,
    );
    sleep(Duration::from_secs(6));
    show(
        HudKind::Done,
        "desktop_window_activate · 12ms url=https://example.com",
        2_500,
    );
    sleep(Duration::from_secs(6));
    show(
        HudKind::Fail,
        "browser_click · timeout selector=#submit",
        2_500,
    );
    sleep(Duration::from_secs(6));
}
