"""SQLite persistent storage for VoiceFlow."""

import logging
import os
import uuid
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

DB_PATH = Path(os.getenv("DB_PATH", str(Path.home() / ".voiceflow" / "voiceflow.db")))


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
                user_id TEXT,
                tenant_id TEXT NOT NULL DEFAULT 'default'
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS snippets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT NOT NULL DEFAULT 'default',
                user_id TEXT NOT NULL DEFAULT '',
                trigger_phrase TEXT NOT NULL,
                expansion TEXT NOT NULL,
                scope TEXT NOT NULL DEFAULT 'personal'
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_dictionary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT NOT NULL DEFAULT 'default',
                user_id TEXT NOT NULL DEFAULT '',
                trigger TEXT NOT NULL,
                replacement TEXT NOT NULL,
                scope TEXT NOT NULL DEFAULT 'personal'
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id         TEXT PRIMARY KEY,
                email      TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                tenant_id  TEXT NOT NULL DEFAULT 'default',
                role       TEXT NOT NULL DEFAULT 'member',
                is_active  INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id)"
        )
        await db.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id  TEXT NOT NULL DEFAULT 'default',
                user_id    TEXT,
                action     TEXT NOT NULL,
                target     TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_tenant ON audit_log(tenant_id, created_at)"
        )
        await db.execute("""
            CREATE TABLE IF NOT EXISTS correction_feedback (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id    TEXT NOT NULL DEFAULT 'default',
                user_id      TEXT,
                raw_whisper  TEXT NOT NULL,
                model_output TEXT NOT NULL,
                user_action  TEXT NOT NULL,
                user_edit    TEXT,
                app_context  TEXT,
                window_title TEXT,
                mode         TEXT,
                language     TEXT,
                created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_feedback_tenant ON correction_feedback(tenant_id, created_at)"
        )
        # Migration: add user_id column if missing (existing DBs)
        async with db.execute("PRAGMA table_info(transcriptions)") as cursor:
            columns = {row[1] async for row in cursor}
        if "user_id" not in columns:
            await db.execute("ALTER TABLE transcriptions ADD COLUMN user_id TEXT")
            logger.info("Migration: added user_id column to transcriptions")
        if "tenant_id" not in columns:
            await db.execute("ALTER TABLE transcriptions ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'default'")
            logger.info("Migration: added tenant_id column to transcriptions")
        if "processing_ms" not in columns:
            await db.execute("ALTER TABLE transcriptions ADD COLUMN processing_ms INTEGER")
            logger.info("Migration: added processing_ms column to transcriptions")
        # Migration: add is_active column to users if missing
        async with db.execute("PRAGMA table_info(users)") as cursor:
            user_columns = {row[1] async for row in cursor}
        if "is_active" not in user_columns:
            await db.execute("ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
            logger.info("Migration: added is_active column to users")
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
    tenant_id: str = "default",
    processing_ms: int | None = None,
) -> int | None:
    """Save a transcription to history. Returns the new row id."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO transcriptions (text, raw_text, corrected, language, duration, mode, user_id, tenant_id, processing_ms) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (text, raw_text, int(corrected), language, duration, mode, user_id, tenant_id, processing_ms),
        )
        await db.commit()
        return cursor.lastrowid


async def get_history(
    limit: int = 100,
    offset: int = 0,
    user_id: str | None = None,
    tenant_id: str = "default",
) -> list[dict]:
    """Return transcription history for a tenant, newest first. Optionally filter by user_id."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if user_id:
            query = "SELECT * FROM transcriptions WHERE tenant_id = ? AND user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params = (tenant_id, user_id, limit, offset)
        else:
            query = "SELECT * FROM transcriptions WHERE tenant_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params = (tenant_id, limit, offset)
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


# ------------------------------------------------------------------
# Dictionary CRUD
# ------------------------------------------------------------------

async def get_dictionary(user_id: str, tenant_id: str = "default") -> list[dict]:
    """Return personal entries for user + all team entries for tenant."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT * FROM user_dictionary
               WHERE tenant_id = ? AND (scope = 'team' OR user_id = ?)
               ORDER BY scope, trigger""",
            (tenant_id, user_id),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def add_dictionary_entry(
    trigger: str,
    replacement: str,
    user_id: str,
    scope: str = "personal",
    tenant_id: str = "default",
) -> int | None:
    """Insert a new dictionary entry. Returns the new row id."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO user_dictionary (tenant_id, user_id, trigger, replacement, scope) VALUES (?, ?, ?, ?, ?)",
            (tenant_id, user_id, trigger.strip(), replacement.strip(), scope),
        )
        await db.commit()
        return cursor.lastrowid


async def get_snippets(user_id: str, tenant_id: str = "default") -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT * FROM snippets
               WHERE tenant_id = ? AND (scope = 'team' OR user_id = ?)
               ORDER BY scope, trigger_phrase""",
            (tenant_id, user_id),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def add_snippet(
    trigger_phrase: str,
    expansion: str,
    user_id: str,
    scope: str = "personal",
    tenant_id: str = "default",
) -> int | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO snippets (tenant_id, user_id, trigger_phrase, expansion, scope) VALUES (?, ?, ?, ?, ?)",
            (tenant_id, user_id, trigger_phrase.strip(), expansion.strip(), scope),
        )
        await db.commit()
        return cursor.lastrowid


async def delete_snippet(snippet_id: int, user_id: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM snippets WHERE id = ? AND user_id = ? AND scope = 'personal'",
            (snippet_id, user_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def delete_dictionary_entry(entry_id: int, user_id: str) -> bool:
    """Delete an entry. Users can only delete their own personal entries."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM user_dictionary WHERE id = ? AND user_id = ? AND scope = 'personal'",
            (entry_id, user_id),
        )
        await db.commit()
        return cursor.rowcount > 0


# ------------------------------------------------------------------
# User CRUD
# ------------------------------------------------------------------

async def create_user(
    email: str,
    password_hash: str,
    tenant_id: str = "default",
    role: str = "member",
) -> str:
    """Insert a new user. Returns the new user id (UUID)."""
    user_id = str(uuid.uuid4())
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO users (id, email, password_hash, tenant_id, role) VALUES (?, ?, ?, ?, ?)",
            (user_id, email, password_hash, tenant_id, role),
        )
        await db.commit()
    return user_id


async def get_user_by_email(email: str) -> dict | None:
    """Return user row as dict or None."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE email = ?", (email,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_user_by_id(user_id: str) -> dict | None:
    """Return user row as dict or None."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def list_users(tenant_id: str) -> list[dict]:
    """Return all users for a tenant."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, email, tenant_id, role, is_active, created_at FROM users WHERE tenant_id = ? ORDER BY created_at",
            (tenant_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def update_user_role(user_id: str, role: str, tenant_id: str) -> bool:
    """Update role for a user within the same tenant. Returns True if updated."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "UPDATE users SET role = ? WHERE id = ? AND tenant_id = ?",
            (role, user_id, tenant_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def deactivate_user(user_id: str, tenant_id: str) -> bool:
    """Soft-delete: set is_active=0. Returns True if updated."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "UPDATE users SET is_active = 0 WHERE id = ? AND tenant_id = ?",
            (user_id, tenant_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def append_audit_log(
    tenant_id: str,
    action: str,
    user_id: str | None = None,
    target: str | None = None,
) -> None:
    """Append an immutable audit log entry (no UPDATE/DELETE on this table)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO audit_log (tenant_id, user_id, action, target) VALUES (?, ?, ?, ?)",
            (tenant_id, user_id, action, target),
        )
        await db.commit()


async def get_audit_log(tenant_id: str, limit: int = 200, offset: int = 0) -> list[dict]:
    """Return audit log entries for a tenant, newest first."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT id, tenant_id, user_id, action, target, created_at
               FROM audit_log
               WHERE tenant_id = ?
               ORDER BY created_at DESC
               LIMIT ? OFFSET ?""",
            (tenant_id, limit, offset),
        ) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def delete_user_data(user_id: str, tenant_id: str) -> dict:
    """KVKK: delete all personal data for a user. Returns counts of deleted rows."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "DELETE FROM transcriptions WHERE user_id = ? AND tenant_id = ?",
            (user_id, tenant_id),
        )
        transcriptions_deleted = cur.rowcount
        cur = await db.execute(
            "DELETE FROM user_dictionary WHERE user_id = ? AND tenant_id = ?",
            (user_id, tenant_id),
        )
        dictionary_deleted = cur.rowcount
        cur = await db.execute(
            "DELETE FROM snippets WHERE user_id = ? AND tenant_id = ?",
            (user_id, tenant_id),
        )
        snippets_deleted = cur.rowcount
        # KVKK: delete feedback data (contains raw_whisper — personal voice data)
        cur = await db.execute(
            "DELETE FROM correction_feedback WHERE user_id = ? AND tenant_id = ?",
            (user_id, tenant_id),
        )
        feedback_deleted = cur.rowcount
        # Soft-delete the user account
        cur = await db.execute(
            "UPDATE users SET is_active = 0 WHERE id = ? AND tenant_id = ?",
            (user_id, tenant_id),
        )
        user_deactivated = cur.rowcount > 0
        await db.commit()
    return {
        "transcriptions_deleted": transcriptions_deleted,
        "dictionary_deleted": dictionary_deleted,
        "snippets_deleted": snippets_deleted,
        "feedback_deleted": feedback_deleted,
        "user_deactivated": user_deactivated,
    }


async def save_feedback(
    raw_whisper: str,
    model_output: str,
    user_action: str,
    tenant_id: str = "default",
    user_id: str | None = None,
    user_edit: str | None = None,
    app_context: str | None = None,
    window_title: str | None = None,
    mode: str | None = None,
    language: str | None = None,
) -> int | None:
    """Save a training feedback entry. Returns the new row id."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO correction_feedback
               (tenant_id, user_id, raw_whisper, model_output, user_action, user_edit, app_context, window_title, mode, language)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (tenant_id, user_id, raw_whisper, model_output, user_action, user_edit, app_context, window_title, mode, language),
        )
        await db.commit()
        return cursor.lastrowid


async def get_tenant_stats(tenant_id: str) -> dict:
    """Tenant bazlı kullanıcı ve transkripsiyon istatistikleri."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Toplam transkripsiyon + kelime + ortalama süre
        async with db.execute(
            """SELECT
                COUNT(*) AS total_transcriptions,
                SUM(length(text) - length(replace(text, ' ', '')) + 1) AS total_words,
                AVG(duration) AS avg_duration
               FROM transcriptions WHERE tenant_id = ?""",
            (tenant_id,),
        ) as cur:
            row = await cur.fetchone()
            total_transcriptions = row["total_transcriptions"] or 0
            total_words = int(row["total_words"] or 0)
            avg_duration = round(row["avg_duration"] or 0.0, 2)

        # Son 7 günde aktif kullanıcı sayısı
        async with db.execute(
            """SELECT COUNT(DISTINCT user_id) AS active_users_7d
               FROM transcriptions
               WHERE tenant_id = ?
                 AND user_id IS NOT NULL
                 AND created_at >= datetime('now', '-7 days')""",
            (tenant_id,),
        ) as cur:
            row = await cur.fetchone()
            active_users_7d = row["active_users_7d"] or 0

        # Mod dağılımı
        async with db.execute(
            """SELECT mode, COUNT(*) AS cnt
               FROM transcriptions
               WHERE tenant_id = ?
               GROUP BY mode""",
            (tenant_id,),
        ) as cur:
            rows = await cur.fetchall()
        mode_breakdown = {"general": 0, "engineering": 0, "office": 0}
        for r in rows:
            key = r["mode"] or "general"
            mode_breakdown[key] = r["cnt"]

        # Aktif kullanıcı sayısı (users tablosu)
        async with db.execute(
            "SELECT COUNT(*) AS total_users FROM users WHERE tenant_id = ? AND is_active = 1",
            (tenant_id,),
        ) as cur:
            row = await cur.fetchone()
            total_users = row["total_users"] or 0

    return {
        "total_transcriptions": total_transcriptions,
        "total_words": total_words,
        "avg_duration": avg_duration,
        "active_users_7d": active_users_7d,
        "total_users": total_users,
        "mode_breakdown": mode_breakdown,
    }
