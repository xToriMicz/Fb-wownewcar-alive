import os
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_DIR = Path(__file__).parent
PROFILES_DIR = PROJECT_DIR / "profiles"


def _load_worker_profile(worker_name: str) -> dict:
    """Load a worker profile from profiles/<name>/worker.json."""
    profile_dir = PROFILES_DIR / worker_name
    config_file = profile_dir / "worker.json"

    if not config_file.exists():
        print(f"Worker profile not found: {config_file}")
        raise SystemExit(1)

    with open(config_file, "r", encoding="utf-8") as f:
        worker = json.load(f)

    limits = worker.get("limits", {})

    return {
        "worker_name": worker_name,

        "page": {
            "url": worker.get("page_url", ""),
            "name": worker.get("page_name", worker_name),
        },

        "persona": {
            "name": worker["persona"]["name"],
            "tone": worker["persona"].get("tone", "chaobaan-fun"),
            "language": "th",
            "description": worker["persona"]["description"],
            "style": worker["persona"]["style"],
        },

        "browser": {
            "profile_dir": str(profile_dir / ".chrome_profile"),
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
            "daily_comment_limit": limits.get("daily_comment_limit", 20),
            "daily_react_limit": limits.get("daily_react_limit", 40),
        },

        "ai": {
            "model": os.getenv("AI_MODEL", "claude-haiku-4-5-20251001"),
            "max_tokens": 200,
        },

        "targets": {
            "pages": worker.get("targets", []),
        },

        "screenshots_dir": str(profile_dir / "screenshots"),
    }


def _default_config() -> dict:
    """Legacy default config (backward compatible)."""
    return {
        "worker_name": "default",

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
            "model": os.getenv("AI_MODEL", "claude-haiku-4-5-20251001"),
            "max_tokens": 200,
        },

        "targets": {
            "pages": [
                "https://www.facebook.com/addzestcarcolor",
                "https://www.facebook.com/PageKruindy",
            ],
        },

        "screenshots_dir": str(PROJECT_DIR / "screenshots"),
    }


def get_worker_name() -> str | None:
    """Extract --worker name from sys.argv."""
    if "--worker" in sys.argv:
        idx = sys.argv.index("--worker")
        if idx + 1 < len(sys.argv):
            return sys.argv[idx + 1]
    return None


def list_workers() -> list[str]:
    """List all available worker profile names."""
    if not PROFILES_DIR.exists():
        return []
    return [d.name for d in PROFILES_DIR.iterdir()
            if d.is_dir() and (d / "worker.json").exists()]


# Load config at import time
_worker = get_worker_name()
if _worker:
    CONFIG = _load_worker_profile(_worker)
else:
    CONFIG = _default_config()
