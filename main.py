"""fb-wownewcar-alive — Facebook Page automation.

Usage:
  python main.py                              # patrol (default worker)
  python main.py --worker wownewcars          # patrol as specific worker
  python main.py --worker wownewcars --mode reply
  python main.py --worker wownewcars --loop   # continuous loop
  python main.py orchestrate                  # launch all workers in parallel
  python main.py login --worker wownewcars    # login for a specific worker
  python main.py list                         # list all workers
"""

import sys
import os
import time
import random
import subprocess

# Fix Windows console encoding for Thai + emoji
if os.name == "nt":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def run_once(page, mode: str):
    """Run a single cycle of the given mode."""
    from patrol import patrol
    from reply import reply_mode

    if mode == "patrol":
        patrol(page)
    elif mode == "reply":
        reply_mode(page)
    elif mode == "post":
        print("Post mode -- coming soon")
    else:
        print(f"Unknown mode: {mode}")
        print("Available: patrol, reply, post")


def run_worker():
    """Run a single worker (one page, one Chrome profile)."""
    from playwright.sync_api import sync_playwright
    from config import CONFIG
    from browser import launch_browser
    from humanize import is_active_hours
    from db import stats_today

    mode = "patrol"
    if "--mode" in sys.argv:
        idx = sys.argv.index("--mode")
        if idx + 1 < len(sys.argv):
            mode = sys.argv[idx + 1]

    loop = "--loop" in sys.argv

    worker_name = CONFIG.get("worker_name", "default")

    if not is_active_hours():
        print(f"[{worker_name}] Outside active hours (08:00-23:00 ICT).")
        return

    print(f"[{worker_name}] mode: {mode}{' (loop)' if loop else ''}")

    with sync_playwright() as pw:
        context, page = launch_browser(pw)

        try:
            if loop:
                _loop(page, worker_name)
            else:
                run_once(page, mode)
        except KeyboardInterrupt:
            print(f"\n[{worker_name}] Stopped by user.")
        except Exception as e:
            print(f"[{worker_name}] Error: {e}")
        finally:
            today = stats_today()
            print(f"\n[{worker_name}] Stats: {today['comments']}c / {today['reactions']}r / {today['replies']}rp")
            print(f"[{worker_name}] Done.")
            if not loop:
                try:
                    input("Press Enter to close browser...")
                except EOFError:
                    pass
            context.close()


def _loop(page, worker_name: str):
    """Continuous loop: patrol -> reply -> sleep -> repeat."""
    from patrol import patrol
    from reply import reply_mode
    from humanize import is_active_hours

    cycle = 0
    while True:
        if not is_active_hours():
            print(f"[{worker_name}] Outside active hours -- sleeping 30 min...")
            time.sleep(1800)
            continue

        cycle += 1
        print(f"\n[{worker_name}] {'='*30} Cycle {cycle} {'='*30}")

        try:
            patrol(page)
        except Exception as e:
            print(f"[{worker_name}] Patrol error: {e}")

        if cycle % 3 == 0:
            try:
                reply_mode(page)
            except Exception as e:
                print(f"[{worker_name}] Reply error: {e}")

        wait_min = random.randint(15, 45)
        print(f"[{worker_name}] Sleeping {wait_min} min...")
        time.sleep(wait_min * 60)


def orchestrate():
    """Launch all workers as separate subprocesses."""
    from config import list_workers

    workers = list_workers()
    if not workers:
        print("No worker profiles found in profiles/")
        print("Create: profiles/<name>/worker.json")
        return

    print(f"Launching {len(workers)} worker(s): {', '.join(workers)}")

    processes = []
    for name in workers:
        cmd = [sys.executable, __file__, "--worker", name, "--loop"]
        print(f"  Starting: {name}")
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        processes.append((name, proc))

    print(f"\nAll workers launched. Ctrl+C to stop all.")
    try:
        while True:
            for name, proc in processes:
                # Print any new output
                if proc.stdout:
                    while True:
                        line = proc.stdout.readline()
                        if not line:
                            break
                        print(f"[{name}] {line}", end="")

                # Check if process died
                if proc.poll() is not None:
                    print(f"[{name}] Exited with code {proc.returncode}")

            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping all workers...")
        for name, proc in processes:
            proc.terminate()
        for name, proc in processes:
            proc.wait(timeout=10)
        print("All workers stopped.")


def login_worker():
    """Login for a specific worker profile."""
    from config import CONFIG
    from playwright.sync_api import sync_playwright

    worker_name = CONFIG.get("worker_name", "default")
    profile_dir = CONFIG["browser"]["profile_dir"]

    print(f"Login for worker: {worker_name}")
    print(f"Chrome profile: {profile_dir}")
    print("Login manually, then close the browser window when done.\n")

    with sync_playwright() as pw:
        context = pw.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            channel="chrome",
            headless=False,
            ignore_default_args=["--enable-automation"],
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1280, "height": 800},
            locale="th-TH",
            timezone_id="Asia/Bangkok",
        )

        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://www.facebook.com/")
        print("Browser opened! Login to Facebook...")

        try:
            while True:
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

    print(f"Session saved for {worker_name}!")


def main():
    # Check for subcommands
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "orchestrate":
            orchestrate()
            return
        if cmd == "login":
            login_worker()
            return
        if cmd == "list":
            from config import list_workers
            workers = list_workers()
            if workers:
                print("Available workers:")
                for w in workers:
                    print(f"  - {w}")
            else:
                print("No workers found. Create profiles/<name>/worker.json")
            return

    run_worker()


if __name__ == "__main__":
    main()
