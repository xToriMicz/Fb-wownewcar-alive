"""Open browser for Facebook login. Run once to save session."""

import time
from playwright.sync_api import sync_playwright

from config import CONFIG

def main():
    print("Opening Chrome for Facebook login...")
    print("Login manually, then close the browser window when done.")
    print()

    with sync_playwright() as pw:
        context = pw.chromium.launch_persistent_context(
            user_data_dir=CONFIG["browser"]["profile_dir"],
            channel="chrome",
            headless=False,
            ignore_default_args=["--enable-automation"],
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-session-crashed-bubble",
                "--disable-restore-session-state",
                "--disable-infobars",
            ],
            viewport={"width": 1280, "height": 800},
            locale="th-TH",
            timezone_id="Asia/Bangkok",
        )

        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://www.facebook.com/")
        print("Browser opened! Login to Facebook...")
        print("(Close the browser window when done)")

        # Wait until browser is closed by user
        try:
            while True:
                # Check if context is still alive
                try:
                    _ = context.pages
                    time.sleep(1)
                except Exception:
                    break
        except KeyboardInterrupt:
            pass

        try:
            context.close()
        except Exception:
            pass

    print("Session saved! You can now run: python main.py")


if __name__ == "__main__":
    main()
