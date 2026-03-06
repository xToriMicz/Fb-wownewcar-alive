"""Reply mode — check our comments for replies, then respond."""

import random
from playwright.sync_api import Page, Locator

from config import CONFIG
from ai import generate_reply
from db import get_our_comments, record_reply, record_reaction
from humanize import human_scroll, random_delay, human_move_to, random_between, sleep_ms

SEL_ARTICLE = '[role="article"]'
SEL_COMMENT_BTN = '[role="button"][aria-label="แสดงความคิดเห็น"]'
SEL_TEXTBOX = '[role="textbox"][aria-label*="ความคิดเห็น"]'


def reply_mode(page: Page):
    """Visit our page, find posts we commented on, reply to new replies."""
    our_page = CONFIG["page"]["url"]
    print(f"\nReply mode — checking: {our_page}")

    # Get our recent comments from DB
    our_comments = get_our_comments(limit=30)
    if not our_comments:
        print("No comments in DB yet. Run patrol first.")
        return

    # Group by target page
    by_target = {}
    for c in our_comments:
        target = c["target_page"] or ""
        by_target.setdefault(target, []).append(c)

    reply_count = 0
    like_count = 0

    for target_url, comments in by_target.items():
        if not target_url:
            continue

        print(f"\nChecking replies on: {target_url}")
        page.goto(target_url)
        sleep_ms(random_between(3000, 5000))

        # Scroll to load posts
        for _ in range(3):
            human_scroll(page)

        for comment_record in comments[:10]:
            try:
                r, l = _find_and_reply(page, comment_record)
                reply_count += r
                like_count += l
                if r or l:
                    random_delay()
            except Exception as e:
                print(f"  Error checking comment #{comment_record['id']}: {e}")

    print(f"\nReply mode done. Replies: {reply_count}, Likes: {like_count}")


def _find_and_reply(page: Page, comment_record: dict) -> tuple[int, int]:
    """Find a post matching our comment, check for replies, respond or like.
    Returns (replies_sent, likes_given)."""
    our_text = comment_record["comment_text"]
    post_text = comment_record["post_text"] or ""
    comment_id = comment_record["id"]
    target = comment_record.get("target_page", "")

    # Try to find our comment on the page by text
    short = our_text[:40].replace('"', '\\"')
    our_comment_el = page.locator(f'div[dir="auto"]:has-text("{short}")').first
    if not our_comment_el.is_visible(timeout=2000):
        return 0, 0

    # Find the parent article
    article = our_comment_el.locator('xpath=ancestor::div[@role="article"]').first

    # Look for reply elements after our comment
    replies_to_us = _find_replies_to_comment(page, article, our_text)

    if not replies_to_us:
        return 0, 0

    print(f"  Found {len(replies_to_us)} reply(ies) to comment #{comment_id}")
    replies_sent = 0
    likes_given = 0

    for their_text in replies_to_us[:2]:
        # 50% chance: just like instead of replying
        if random.random() < 0.5:
            liked = _like_reply(page, article, their_text)
            if liked:
                likes_given += 1
                record_reaction(their_text, target, reaction_type="like_reply")
                print(f'  Liked reply: "{their_text[:50]}..."')
                sleep_ms(random_between(1000, 2000))
            continue

        reply_text = generate_reply(post_text, their_text)
        if not reply_text:
            continue

        success = _send_reply(page, article, reply_text)
        if success:
            record_reply(their_text, reply_text, comment_id=comment_id)
            replies_sent += 1
            print(f'  Replied: "{reply_text}"')
            sleep_ms(random_between(2000, 4000))

    return replies_sent, likes_given


def _find_replies_to_comment(page: Page, article: Locator, our_text: str) -> list[str]:
    """Find text of replies to our comment within an article."""
    replies = []
    try:
        # All text blocks in this article area
        all_texts = article.locator('div[dir="auto"]')
        count = all_texts.count()
        found_ours = False

        for i in range(count):
            text = all_texts.nth(i).inner_text().strip()
            if not text or len(text) > 300:
                continue

            # Our comment text (partial match)
            if our_text[:30] in text:
                found_ours = True
                continue

            # After finding ours, next text blocks are likely replies
            if found_ours and text != our_text and len(text) > 2:
                replies.append(text)
                if len(replies) >= 3:
                    break
    except Exception:
        pass
    return replies


def _like_reply(page: Page, article: Locator, reply_text: str) -> bool:
    """Like a specific reply comment by finding its like button."""
    try:
        short = reply_text[:30].replace('"', '\\"')
        reply_el = article.locator(f'div[dir="auto"]:has-text("{short}")').first
        if not reply_el.is_visible(timeout=2000):
            return False

        # Find the nearest like button relative to this reply text
        # Facebook reply like buttons are typically nearby in the DOM
        reply_container = reply_el.locator('xpath=ancestor::div[@role="article"]').first
        like_btn = reply_container.locator('[role="button"][aria-label="ถูกใจ"]').first
        if like_btn.count() > 0:
            like_btn.click(force=True)
            return True
    except Exception:
        pass
    return False


def _send_reply(page: Page, article: Locator, text: str) -> bool:
    """Send a reply within an article's comment thread."""
    try:
        # Look for reply button (ตอบกลับ) or existing textbox
        reply_btn = article.locator('[role="button"]:has-text("ตอบกลับ")').first
        if reply_btn.is_visible(timeout=2000):
            reply_btn.click(force=True)
            sleep_ms(random_between(1000, 2000))

        # Find the textbox
        textbox = article.locator(SEL_TEXTBOX).first
        if not textbox.is_visible(timeout=2000):
            textbox = page.locator(SEL_TEXTBOX).first
        if not textbox.is_visible(timeout=2000):
            print("  No reply textbox found")
            return False

        textbox.click(force=True)
        sleep_ms(300)
        textbox.evaluate("el => el.focus()")
        sleep_ms(300)

        h = CONFIG["humanize"]
        for char in text:
            page.keyboard.type(char, delay=random_between(h["type_delay_min"], h["type_delay_max"]))

        sleep_ms(random_between(500, 1500))

        # Try form submit button
        form = textbox.locator('xpath=ancestor::form')
        if form.count() > 0:
            send_btn = form.locator('[role="button"][aria-label="แสดงความคิดเห็น"]').first
            if send_btn.count() > 0:
                send_btn.click(force=True)
                sleep_ms(3000)
                return True

        # Fallback: Enter key
        textbox.press("Enter")
        sleep_ms(3000)
        return True

    except Exception as e:
        print(f"  Reply send failed: {e}")
        return False
