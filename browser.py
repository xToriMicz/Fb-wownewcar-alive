"""Browser launcher — fresh persistent profile (login once via login.py)."""

from pathlib import Path
from playwright.sync_api import BrowserContext, Page

from config import CONFIG

SANDBOX_DIR = Path(CONFIG["browser"]["profile_dir"])

LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-session-crashed-bubble",
    "--disable-restore-session-state",
    "--disable-infobars",
    "--disable-notifications",
    "--disable-popup-blocking",
    "--disable-default-apps",
    "--disable-features=PasswordCheck,PasswordLeakDetection,PasswordImport,PasswordGeneration",
    "--password-store=basic",
    "--disable-translate",
]


def launch_browser(pw) -> tuple[BrowserContext, Page]:
    if not (SANDBOX_DIR / "Default").exists():
        print("No profile found! Run 'python login.py' first to login to Facebook.")
        raise SystemExit(1)

    context = pw.chromium.launch_persistent_context(
        user_data_dir=str(SANDBOX_DIR),
        channel="chrome",
        headless=CONFIG["browser"]["headless"],
        slow_mo=CONFIG["browser"]["slow_mo"],
        args=LAUNCH_ARGS,
        ignore_default_args=["--enable-automation"],
        viewport={"width": 1280, "height": 800},
        locale="th-TH",
        timezone_id="Asia/Bangkok",
    )

    page = context.pages[0] if context.pages else context.new_page()
    return context, page
