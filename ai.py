"""AI comment generation using Claude API."""

import anthropic
from config import CONFIG

client = anthropic.Anthropic()
persona = CONFIG["persona"]

SYSTEM_PROMPT = f"""You are the social media voice of "{persona['name']}".
{persona['description']}

Style rules:
{chr(10).join('- ' + s for s in persona['style'])}

IMPORTANT:
- Reply in Thai ONLY (ภาษาพูด ไม่ใช่ภาษาเขียน)
- Sound like ชาวบ้านทั่วไป NOT a brand, NOT a bot
- Match the energy — ตลกก็ขำด้วย ตื่นเต้นก็ตื่นเต้นด้วย
- Never mention you are AI or a bot
- NEVER use formal language, corporate tone, or emojis spam"""

INTENSITY_GUIDE = {
    "soft": """Reply with ONLY one of these styles:
- Single emoji reaction (e.g. 😂, 🔥, 💀, 😭, 👏)
- Very short reaction (e.g. "555+", "โคตรเลย", "จริงดิ", "บ้าไปแล้ว", "แม่เจ้า")
- Short phrase + emoji (e.g. "สวยว่ะ 🔥", "ตายแล้ว 555")
MAX 5 words. เน้นเนียน กลมกลืนกับคอมเม้นคนอื่น.""",

    "medium": """Reply SHORT (1 sentence max). Follow the vibe of other comments.
Can add a small opinion or reaction. เช่น "โอ้โห คันนี้สวยจริงว่ะ" or "555 จอดแบบนี้ก็ได้เหรอ"
MAX 10 words.""",

    "full": """Reply naturally 1-2 sentences. Can ask a question to get people talking.
เช่น "เฮ้ย ใครเคยเจอแบบนี้บ้าง?" or "บ้าไปแล้ว นี่มันยังไง ใครรู้บ้าง" """,
}


def generate_comment(post_content: str, existing_comments: list[str], intensity: str = "soft") -> str:
    comment_ctx = ""
    if existing_comments:
        lines = "\n".join(f'{i+1}. "{c}"' for i, c in enumerate(existing_comments))
        comment_ctx = f"\n\nTop comments from others:\n{lines}"

    guide = INTENSITY_GUIDE.get(intensity, INTENSITY_GUIDE["soft"])

    response = client.messages.create(
        model=CONFIG["ai"]["model"],
        max_tokens=CONFIG["ai"]["max_tokens"],
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": (
                f'You see this post on Facebook:\n\n"{post_content}"{comment_ctx}\n\n'
                f"{guide}\n\n"
                "Blend in with the crowd. Don't stand out. Comment like everyone else is commenting."
            ),
        }],
    )

    if response.content and response.content[0].type == "text":
        return response.content[0].text.strip()
    return ""


def generate_reply(original_post: str, their_comment: str) -> str:
    response = client.messages.create(
        model=CONFIG["ai"]["model"],
        max_tokens=CONFIG["ai"]["max_tokens"],
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": (
                f'Someone replied to your comment:\n\n'
                f'Original post: "{original_post}"\n'
                f'Their reply: "{their_comment}"\n\n'
                "Reply back like a normal Thai person chatting. Short, fun, keep the conversation going."
            ),
        }],
    )

    if response.content and response.content[0].type == "text":
        return response.content[0].text.strip()
    return ""


def generate_post_idea(topic: str | None = None) -> dict:
    topic_text = f" Topic: {topic}" if topic else " Pick something fun — could be car content, funny clip, or something viral."

    response = client.messages.create(
        model=CONFIG["ai"]["model"],
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": (
                f'Create a Facebook post for {persona["name"]} page.{topic_text}\n\n'
                'Return JSON format:\n'
                '{"text": "post content here", "hashtags": ["tag1", "tag2"]}\n\n'
                'Make it บ้าๆบอๆ, engaging, ถามคำถามให้คนอยากตอบ. ภาษาชาวบ้าน ไม่ต้องสุภาพ.\n'
                'ตัวอย่าง tone: "เฮ้ย ใครเคยเจอแบบนี้บ้าง 555", "จอดแบบนี้ก็ได้เหรอวะ"'
            ),
        }],
    )

    if response.content and response.content[0].type == "text":
        import json, re
        match = re.search(r"\{[\s\S]*\}", response.content[0].text)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
    return {"text": "", "hashtags": []}
