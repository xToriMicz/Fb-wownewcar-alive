"""fb-wownewcar-alive — Facebook Page automation."""

import sys
import os
import time
import random

# Fix Windows console encoding for Thai + emoji
if os.name == "nt":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from playwright.sync_api import sync_playwright

from config import CONFIG
from browser import launch_browser
from humanize import is_active_hours
from patrol import patrol
from reply import reply_mode
from db import stats_today


def run_once(page, mode: str):
    """Run a single cycle of the given mode."""
    if mode == "patrol":
        patrol(page)
    elif mode == "reply":
        reply_mode(page)
    elif mode == "post":
        print("Post mode — coming soon")
    else:
        print(f"Unknown mode: {mode}")
        print("Available: patrol, reply, post, loop")


def main():
    mode = "patrol"
    if "--mode" in sys.argv:
        idx = sys.argv.index("--mode")
        if idx + 1 < len(sys.argv):
            mode = sys.argv[idx + 1]

    loop = "--loop" in sys.argv or mode == "loop"

    if not is_active_hours():
        print("Outside active hours (08:00-23:00 ICT). Sleeping.")
        return

    print(f"fb-wownewcar-alive | mode: {mode}{' (loop)' if loop else ''}")

    with sync_playwright() as pw:
        context, page = launch_browser(pw)

        try:
            if loop:
                _loop(page)
            else:
                run_once(page, mode)
        except KeyboardInterrupt:
            print("\nStopped by user.")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            today = stats_today()
            print(f"\nSession stats: {today['comments']}c / {today['reactions']}r / {today['replies']}rp")
            print("Done.")
            if not loop:
                try:
                    input("Press Enter to close browser...")
                except EOFError:
                    pass
            context.close()


def _loop(page):
    """Continuous loop: patrol → reply → sleep → repeat."""
    cycle = 0
    while True:
        if not is_active_hours():
            print("Outside active hours — sleeping 30 min...")
            time.sleep(1800)
            continue

        cycle += 1
        print(f"\n{'='*40}")
        print(f"Cycle {cycle}")
        print(f"{'='*40}")

        try:
            patrol(page)
        except Exception as e:
            print(f"Patrol error: {e}")

        # Every 3rd cycle, also do reply check
        if cycle % 3 == 0:
            try:
                reply_mode(page)
            except Exception as e:
                print(f"Reply error: {e}")

        # Random sleep between cycles (15-45 min)
        wait_min = random.randint(15, 45)
        print(f"\nSleeping {wait_min} min until next cycle...")
        time.sleep(wait_min * 60)


if __name__ == "__main__":
    main()
