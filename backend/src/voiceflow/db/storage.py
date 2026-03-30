"""SQLite persistent storage for VoiceFlow."""

import logging
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

DB_PATH = Path.home() / ".voiceflow" / "voiceflow.db"


async def init_db() -> None:
    """Create database and tables if they don't exist. Runs migrations for existing DBs."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS transcriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                text TEXT NOT NULL,
                raw_text TEXT,
                corrected INTEGER DEFAULT 0,
                language TEXT,
                duration REAL,
                mode TEXT DEFAULT 'general',
                user_id TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        # Migration: add user_id column if missing (existing DBs)
        async with db.execute("PRAGMA table_info(transcriptions)") as cursor:
            columns = {row[1] async for row in cursor}
        if "user_id" not in columns:
            await db.execute("ALTER TABLE transcriptions ADD COLUMN user_id TEXT")
            logger.info("Migration: added user_id column to transcriptions")
        await db.commit()
    logger.info("Database initialized at %s", DB_PATH)


async def save_transcription(
    text: str,
    raw_text: str | None = None,
    corrected: bool = False,
    language: str | None = None,
    duration: float | None = None,
    mode: str = "general",
    user_id: str | None = None,
) -> int | None:
    """Save a transcription to history. Returns the new row id."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO transcriptions (text, raw_text, corrected, language, duration, mode, user_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (text, raw_text, int(corrected), language, duration, mode, user_id),
        )
        await db.commit()
        return cursor.lastrowid


async def get_history(limit: int = 100, offset: int = 0, user_id: str | None = None) -> list[dict]:
    """Return transcription history, newest first. Optionally filter by user_id."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if user_id:
            query = "SELECT * FROM transcriptions WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params = (user_id, limit, offset)
        else:
            query = "SELECT * FROM transcriptions ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params = (limit, offset)
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def clear_history() -> None:
    """Delete all transcription history."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM transcriptions")
        await db.commit()


async def get_config(key: str, default: str | None = None) -> str | None:
    """Get a config value by key."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM config WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else default


async def set_config(key: str, value: str) -> None:
    """Set a config value (upsert)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, value)
        )
        await db.commit()
