"""Human-like behavior — delays, typing, scrolling."""

import random
import time
from datetime import datetime, timezone, timedelta
from playwright.sync_api import Page

from config import CONFIG

H = CONFIG["humanize"]
ICT = timezone(timedelta(hours=7))


def random_between(a: int, b: int) -> int:
    return random.randint(a, b)


def random_delay():
    """Sleep random seconds within action delay range."""
    sec = random_between(H["action_delay_min"], H["action_delay_max"])
    time.sleep(sec)


def sleep_ms(ms: int):
    time.sleep(ms / 1000)


def human_type(page: Page, selector: str, text: str):
    """Type text character by character like a real person."""
    page.click(selector)
    sleep_ms(random_between(300, 800))

    for char in text:
        page.keyboard.type(char, delay=random_between(H["type_delay_min"], H["type_delay_max"]))


def human_type_into(page: Page, locator, text: str):
    """Type into a locator element character by character."""
    # Use force click to bypass overlay elements (Facebook often has overlays)
    locator.click(force=True)
    sleep_ms(random_between(300, 800))

    # Also focus via JS as backup
    try:
        locator.evaluate("el => el.focus()")
    except Exception:
        pass

    sleep_ms(200)

    for char in text:
        page.keyboard.type(char, delay=random_between(H["type_delay_min"], H["type_delay_max"]))


def human_scroll(page: Page):
    """Scroll down by random amount."""
    amount = random_between(300, 700)
    page.mouse.wheel(0, amount)
    sleep_ms(random_between(1000, 3000))


def is_active_hours() -> bool:
    """Check if within active hours (ICT)."""
    now = datetime.now(ICT)
    return H["active_hours_start"] <= now.hour < H["active_hours_end"]


def human_move_to(page: Page, locator):
    """Move mouse to element with slight randomness."""
    try:
        box = locator.bounding_box()
        if not box:
            return
        x = box["x"] + random_between(5, max(10, int(box["width"]) - 5))
        y = box["y"] + random_between(5, max(10, int(box["height"]) - 5))
        page.mouse.move(x, y, steps=random_between(5, 15))
        sleep_ms(random_between(200, 500))
    except Exception:
        pass
