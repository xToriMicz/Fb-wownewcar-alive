import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_DIR = Path(__file__).parent

CONFIG = {
    "page": {
        "url": os.getenv("FACEBOOK_PAGE_URL", "https://www.facebook.com/wownewcars"),
        "name": "Wow New Cars",
    },

    "persona": {
        "name": "Wow New Cars",
        "tone": "chaobaan-fun",
        "language": "th",
        "description": "เพจบ้าๆบอๆ คลิปรถ คลิปตลก คลิปตกใจ เน้นคนมีส่วนร่วม engagement สูง",
        "style": [
            "พูดแบบชาวบ้านทั่วไป ภาษาพูด ไม่เป็นทางการ",
            "ตลก บ้าๆบอๆ ขำๆ ใช้ 555 ได้เลย",
            "ชอบแซว ชอบถามให้คนตอบ เช่น 'มีใครเคยเจอแบบนี้บ้าง?'",
            "ใช้คำว่า โคตร, บ้าไปแล้ว, เฮ้ย, จริงดิ, ตายแล้ว, แม่เจ้า",
            "บางทีพิมพ์ผิดนิดหน่อยก็ได้ ดูเป็นธรรมชาติ",
            "ตอบสั้นๆ 1-2 ประโยค เหมือนพิมพ์เร็วๆ",
            "ถ้าเป็นคลิปรถ ก็ตื่นเต้นด้วย ถ้าคลิปตลก ก็ขำด้วย",
        ],
    },

    "browser": {
        "profile_dir": str(PROJECT_DIR / ".chrome_profile"),
        "headless": False,
        "slow_mo": 50,
    },

    "humanize": {
        "type_delay_min": 30,
        "type_delay_max": 120,
        "action_delay_min": 3,
        "action_delay_max": 15,
        "active_hours_start": 8,
        "active_hours_end": 23,
        "daily_comment_limit": 20,
        "daily_react_limit": 40,
    },

    "ai": {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 200,
    },

    "targets": {
        "pages": [
            "https://www.facebook.com/addzestcarcolor",
            "https://www.facebook.com/PageKruindy",
        ],
    },
}
