"""SQLite tracking — comments, reactions, replies."""

import sqlite3
from pathlib import Path
from datetime import datetime, timezone, timedelta

DB_PATH = Path(__file__).parent / "tracker.db"
ICT = timezone(timedelta(hours=7))


def _now_ict() -> str:
    return datetime.now(ICT).isoformat()


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _init_tables(conn)
    return conn


def _init_tables(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            worker TEXT DEFAULT 'default',
            post_url TEXT,
            post_text TEXT,
            comment_text TEXT NOT NULL,
            target_page TEXT,
            intensity TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS reactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            worker TEXT DEFAULT 'default',
            post_url TEXT,
            post_text TEXT,
            target_page TEXT,
            reaction_type TEXT DEFAULT 'like',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS replies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            worker TEXT DEFAULT 'default',
            comment_id INTEGER REFERENCES comments(id),
            their_comment TEXT,
            our_reply TEXT NOT NULL,
            post_url TEXT,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_comments_post ON comments(post_text);
        CREATE INDEX IF NOT EXISTS idx_comments_target ON comments(target_page);
        CREATE INDEX IF NOT EXISTS idx_comments_worker ON comments(worker);
    """)


def _get_worker() -> str:
    """Get current worker name from config."""
    try:
        from config import CONFIG
        return CONFIG.get("worker_name", "default")
    except Exception:
        return "default"


def record_comment(post_text: str, comment_text: str, target_page: str,
                   intensity: str = "", post_url: str = "") -> int:
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO comments (worker, post_url, post_text, comment_text, target_page, intensity, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (_get_worker(), post_url, post_text[:500], comment_text, target_page, intensity, _now_ict()),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def record_reaction(post_text: str, target_page: str, reaction_type: str = "like",
                    post_url: str = "") -> int:
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO reactions (worker, post_url, post_text, target_page, reaction_type, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (_get_worker(), post_url, post_text[:500], target_page, reaction_type, _now_ict()),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def record_reply(their_comment: str, our_reply: str, comment_id: int = None,
                 post_url: str = "") -> int:
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO replies (worker, comment_id, their_comment, our_reply, post_url, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (_get_worker(), comment_id, their_comment, our_reply, post_url, _now_ict()),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def already_commented_on(post_text: str) -> bool:
    """Check if this worker already commented on a post (by text prefix match)."""
    conn = get_db()
    prefix = post_text[:200]
    worker = _get_worker()
    row = conn.execute(
        "SELECT 1 FROM comments WHERE worker = ? AND post_text LIKE ? LIMIT 1",
        (worker, prefix + "%"),
    ).fetchone()
    conn.close()
    return row is not None


def get_our_comments(limit: int = 50) -> list[dict]:
    """Get recent comments posted by this worker."""
    conn = get_db()
    worker = _get_worker()
    rows = conn.execute(
        "SELECT * FROM comments WHERE worker = ? ORDER BY id DESC LIMIT ?",
        (worker, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_unreplied_comment_ids() -> list[int]:
    """Get comment IDs that haven't received a reply yet."""
    conn = get_db()
    rows = conn.execute(
        "SELECT c.id FROM comments c "
        "LEFT JOIN replies r ON r.comment_id = c.id "
        "WHERE r.id IS NULL "
        "ORDER BY c.id DESC LIMIT 20"
    ).fetchall()
    conn.close()
    return [r["id"] for r in rows]


def get_comment_by_id(comment_id: int) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM comments WHERE id = ?", (comment_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def stats_today(worker: str = None) -> dict:
    """Get today's stats for a specific worker (or current worker)."""
    conn = get_db()
    w = worker or _get_worker()
    today = datetime.now(ICT).strftime("%Y-%m-%d")
    comments = conn.execute(
        "SELECT COUNT(*) as n FROM comments WHERE worker = ? AND created_at LIKE ?",
        (w, today + "%"),
    ).fetchone()["n"]
    reactions = conn.execute(
        "SELECT COUNT(*) as n FROM reactions WHERE worker = ? AND created_at LIKE ?",
        (w, today + "%"),
    ).fetchone()["n"]
    replies = conn.execute(
        "SELECT COUNT(*) as n FROM replies WHERE worker = ? AND created_at LIKE ?",
        (w, today + "%"),
    ).fetchone()["n"]
    conn.close()
    return {"comments": comments, "reactions": reactions, "replies": replies}


def stats_all_workers() -> list[dict]:
    """Get today's stats for all workers."""
    conn = get_db()
    today = datetime.now(ICT).strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT worker, COUNT(*) as comments FROM comments "
        "WHERE created_at LIKE ? GROUP BY worker",
        (today + "%",),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
