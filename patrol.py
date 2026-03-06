"""Patrol target pages — read the room, then blend in."""

import random
import os
from playwright.sync_api import Page, Locator

from config import CONFIG
from ai import generate_comment
from db import already_commented_on, record_comment, record_reaction, stats_today
from humanize import human_scroll, random_delay, human_move_to, random_between, sleep_ms

# Facebook Thai locale selectors (inspected Mar 2026)
# Post structure: [role="feed"] > ... > [role="article"] > ... > [data-ad-rendering-role="story_message"]
# Comment button, like button, textbox are all INSIDE the same [role="article"]
SEL_POST_TEXT = '[data-ad-rendering-role="story_message"]'
SEL_ARTICLE = 'xpath=ancestor::div[@role="article"]'
SEL_COMMENT_BTN = '[role="button"][aria-label="แสดงความคิดเห็น"]'
SEL_LIKE_BTN = '[role="button"][aria-label="ถูกใจ"]'
SEL_TEXTBOX = '[role="textbox"][aria-label*="ความคิดเห็น"]'
# Comments are nested [role="article"] inside the post article
# When used via article.locator(), this finds comment articles within the post
SEL_EXISTING_COMMENTS = '[role="article"] div[dir="auto"]'


def patrol(page: Page):
    targets = CONFIG["targets"]["pages"]
    if not targets:
        print("No target pages configured.")
        return

    comment_count = 0
    react_count = 0
    screenshots_dir = CONFIG.get("screenshots_dir", "screenshots")
    os.makedirs(screenshots_dir, exist_ok=True)

    today = stats_today()
    print(f"Today so far: {today['comments']} comments, {today['reactions']} reactions, {today['replies']} replies")

    for target_url in targets:
        print(f"\nPatrolling: {target_url}")
        page.goto(target_url)
        sleep_ms(random_between(3000, 5000))

        post_count = random_between(3, 6)
        for i in range(post_count):
            human_scroll(page)

            posts = page.locator(SEL_POST_TEXT)
            count = posts.count()
            if count == 0:
                continue

            post_index = min(i, count - 1)
            post = posts.nth(post_index)

            try:
                post_text = post.inner_text()
                if not post_text.strip():
                    continue

                print(f"\nPost {i + 1}: {post_text[:80]}...")

                # Get the article container (parent of everything)
                article = post.locator(SEL_ARTICLE).first

                # Step 1: Read existing comments (vibe check)
                existing = _scrape_top_comments(article)
                if existing:
                    print(f"  Vibe ({len(existing)} comments):")
                    for c in existing[:3]:
                        print(f'    - "{c}"')

                # Check if we already commented on this post (DB + DOM)
                if already_commented_on(post_text) or _already_commented(article):
                    print("  Already commented — skipping")
                    continue

                # Step 2: Decide action
                roll = random.random()
                if roll < 0.3 and comment_count < CONFIG["humanize"]["daily_comment_limit"]:
                    intensity = _pick_intensity(comment_count)
                    comment_text = generate_comment(post_text, existing, intensity)

                    if comment_text:
                        success = _comment_on_post(page, article, comment_text)
                        if success:
                            comment_count += 1
                            record_comment(post_text, comment_text, target_url, intensity)
                            print(f'  Commented [{intensity}]: "{comment_text}"')
                            _screenshot_our_comment(page, article, comment_text, comment_count, screenshots_dir)
                        else:
                            print(f'  Failed to post: "{comment_text}"')

                elif roll < 0.7 and react_count < CONFIG["humanize"]["daily_react_limit"]:
                    if _react_to_post(page, article):
                        react_count += 1
                        record_reaction(post_text, target_url)

                else:
                    print("  Scrolled past")

                random_delay()

            except Exception as e:
                print(f"  Skipped post {i + 1}: {e}")

    print(f"\nPatrol done. Comments: {comment_count}, Reacts: {react_count}")


def _scrape_top_comments(article: Locator) -> list[str]:
    """Read visible comments inside an article."""
    comments = []
    try:
        comment_els = article.locator(SEL_EXISTING_COMMENTS)
        count = min(comment_els.count(), 5)
        for i in range(count):
            text = comment_els.nth(i).inner_text()
            if text.strip() and len(text) < 200:
                comments.append(text.strip())
    except Exception:
        pass
    return comments


def _already_commented(article: Locator) -> bool:
    """Check if Wownewcars already commented on this post."""
    try:
        # Look for our page name in comment authors within the article
        our_comments = article.locator('a:has-text("Wownewcars")')
        return our_comments.count() > 0
    except Exception:
        return False


def _pick_intensity(comments_so_far: int) -> str:
    if comments_so_far < 5:
        return "soft"
    if comments_so_far < 12:
        return "medium"
    return "full"


def _comment_on_post(page: Page, article: Locator, text: str) -> bool:
    """Click comment button inside article, type, and send."""
    try:
        # Find comment button INSIDE this article
        comment_btn = article.locator(SEL_COMMENT_BTN).first
        if comment_btn.count() == 0:
            print("  No comment button in article")
            return False

        # Scroll into view + click (force to bypass overlay interception)
        comment_btn.scroll_into_view_if_needed(timeout=5000)
        sleep_ms(500)
        human_move_to(page, comment_btn)
        comment_btn.click(force=True)
        sleep_ms(random_between(1500, 2500))

        # Find textbox — try within article first, then page-wide
        textbox = article.locator(SEL_TEXTBOX).first
        if not textbox.is_visible(timeout=2000):
            textbox = page.locator(SEL_TEXTBOX).first
        if not textbox.is_visible(timeout=2000):
            # Fallback: textbox with page name
            textbox = page.locator('[role="textbox"][aria-label*="Wownewcars"]').first
        if not textbox.is_visible(timeout=1000):
            print("  No textbox found")
            return False

        # Focus + type character by character
        textbox.click(force=True)
        sleep_ms(300)
        textbox.evaluate("el => el.focus()")
        sleep_ms(300)

        h = CONFIG["humanize"]
        for char in text:
            page.keyboard.type(char, delay=random_between(h["type_delay_min"], h["type_delay_max"]))

        sleep_ms(random_between(500, 1500))

        # Try multiple send methods
        sent = _try_send_comment(page, textbox)
        if not sent:
            print("  All send methods failed")
            return False

        sleep_ms(3000)
        return True

    except Exception as e:
        print(f"  Comment failed: {e}")
        return False


def _try_send_comment(page: Page, textbox: Locator) -> bool:
    """Try multiple methods to submit the comment."""
    # Method 1: Find submit button inside the same <form> as the textbox
    # The form contains: textbox + emoji/sticker/photo buttons + submit button
    # Submit button has aria-label="แสดงความคิดเห็น" (same text as comment button but inside form)
    try:
        form = textbox.locator('xpath=ancestor::form')
        if form.count() > 0:
            send_btn = form.locator('[role="button"][aria-label="แสดงความคิดเห็น"]').first
            if send_btn.count() > 0:
                send_btn.click(force=True)
                print("  Sent via form submit button")
                return True
    except Exception:
        pass

    # Method 2: textbox.press("Enter") — focused on the right element
    try:
        textbox.press("Enter")
        sleep_ms(2000)

        # Check if Share dialog appeared (wrong target)
        share_dialog = page.locator('[role="dialog"][aria-label*="แชร์"]')
        if share_dialog.count() > 0 and share_dialog.first.is_visible():
            print("  Share dialog detected — dismissing")
            page.keyboard.press("Escape")
            sleep_ms(1000)
        else:
            print("  Sent via Enter key")
            return True
    except Exception:
        pass

    # Method 3: Re-focus textbox and use keyboard
    try:
        textbox.click(force=True)
        sleep_ms(300)
        textbox.evaluate("el => el.focus()")
        sleep_ms(200)
        page.keyboard.press("Enter")
        sleep_ms(2000)
        print("  Sent via keyboard Enter (refocused)")
        return True
    except Exception:
        pass

    return False


def _screenshot_our_comment(page: Page, article: Locator, comment_text: str, count: int,
                            screenshots_dir: str = "screenshots"):
    """Take a targeted screenshot of our comment element."""
    path = f"{screenshots_dir}/comment_{count}.png"
    try:
        short = comment_text[:30].replace('"', '\\"')
        our_el = article.locator(f'div[dir="auto"]:has-text("{short}")').first
        if our_el.is_visible(timeout=3000):
            our_el.screenshot(path=path)
            print(f"  Screenshot: {path} (element)")
            return
    except Exception:
        pass
    try:
        article.screenshot(path=path)
        print(f"  Screenshot: {path} (article fallback)")
    except Exception:
        page.screenshot(path=path)
        print(f"  Screenshot: {path} (full page fallback)")


def _react_to_post(page: Page, article: Locator) -> bool:
    """Click like button inside article."""
    try:
        like_btn = article.locator(SEL_LIKE_BTN).first
        if like_btn.count() == 0:
            print("  No like button in article")
            return False

        like_btn.scroll_into_view_if_needed(timeout=5000)
        sleep_ms(500)
        # Use force=True — Facebook images/overlays often intercept clicks
        like_btn.click(force=True)
        print("  Reacted (Like)")
        return True

    except Exception as e:
        print(f"  React failed: {e}")
        return False
