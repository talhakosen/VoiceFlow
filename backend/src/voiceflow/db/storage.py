"""SQLite persistent storage for VoiceFlow."""

import logging
import uuid

from .cipher_connection import connect as _sqlcipher_connect
from ..core.config import DB_PATH


class _AiosqliteCompat:
    """Drop-in shim: `aiosqlite.connect(path)` → cipher_connection.connect(path)."""
    def connect(self, path):
        return _sqlcipher_connect(path)


aiosqlite = _AiosqliteCompat()

logger = logging.getLogger(__name__)


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
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_transcriptions_tenant_date ON transcriptions(tenant_id, created_at)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_dict_trigger ON user_dictionary(trigger)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_snippets_user ON snippets(user_id)"
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
        await db.execute("""
            CREATE TABLE IF NOT EXISTS symbol_index (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id    TEXT NOT NULL DEFAULT 'default',
                user_id      TEXT NOT NULL DEFAULT '',
                project_path TEXT NOT NULL DEFAULT '',
                file_path    TEXT NOT NULL,
                symbol_type  TEXT NOT NULL,
                symbol_name  TEXT NOT NULL,
                line_number  INTEGER NOT NULL
            )
        """)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_symbol_user ON symbol_index(user_id, symbol_name)"
        )
        await db.execute("""
            CREATE TABLE IF NOT EXISTS symbol_index_v2 (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id     TEXT NOT NULL DEFAULT 'default',
                user_id       TEXT NOT NULL DEFAULT '',
                project_path  TEXT NOT NULL DEFAULT '',
                file_path     TEXT NOT NULL,
                symbol_type   TEXT NOT NULL,
                symbol_name   TEXT NOT NULL,
                line_number   INTEGER NOT NULL,
                end_line      INTEGER,
                signature     TEXT,
                parent_symbol TEXT,
                parent_class  TEXT,
                conformances  TEXT,
                return_type   TEXT,
                properties    TEXT,
                imports       TEXT,
                decorators    TEXT,
                visibility    TEXT,
                is_static     INTEGER DEFAULT 0,
                indexed_at    TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_symbol_v2_user   ON symbol_index_v2(user_id, symbol_name)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_symbol_v2_type   ON symbol_index_v2(user_id, symbol_type)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_symbol_v2_parent ON symbol_index_v2(user_id, parent_symbol)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_symbol_v2_file   ON symbol_index_v2(user_id, file_path)"
        )
        await db.execute("""
            CREATE TABLE IF NOT EXISTS training_sentences (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id    TEXT NOT NULL DEFAULT 'default',
                training_set TEXT NOT NULL DEFAULT 'it_dataset',
                persona      TEXT,
                scenario     TEXT,
                text         TEXT NOT NULL
            )
        """)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_ts_set ON training_sentences(training_set)"
        )
        await db.execute("""
            CREATE TABLE IF NOT EXISTS training_recordings (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id    TEXT NOT NULL DEFAULT 'default',
                sentence_id  INTEGER NOT NULL REFERENCES training_sentences(id),
                training_set TEXT NOT NULL DEFAULT 'it_dataset',
                wav_path     TEXT NOT NULL,
                whisper_out  TEXT,
                duration_ms  INTEGER,
                created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_tr_sentence ON training_recordings(sentence_id)"
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
        if "whisper_model" not in columns:
            await db.execute("ALTER TABLE transcriptions ADD COLUMN whisper_model TEXT")
            logger.info("Migration: added whisper_model column to transcriptions")
        # Migration: add is_active column to users if missing
        async with db.execute("PRAGMA table_info(users)") as cursor:
            user_columns = {row[1] async for row in cursor}
        if "is_active" not in user_columns:
            await db.execute("ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
            logger.info("Migration: added is_active column to users")

        # Migration: add tenant_id to training and symbol tables
        for table in ("training_sentences", "training_recordings", "symbol_index", "symbol_index_v2"):
            async with db.execute(f"PRAGMA table_info({table})") as cursor:  # noqa: S608
                cols = {row[1] async for row in cursor}
            if "tenant_id" not in cols:
                await db.execute(f"ALTER TABLE {table} ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'default'")  # noqa: S608
                logger.info("Migration: added tenant_id to %s", table)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS token_blacklist (
                jti        TEXT PRIMARY KEY,
                expires_at TEXT NOT NULL,
                revoked_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_blacklist_exp ON token_blacklist(expires_at)"
        )

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
    whisper_model: str | None = None,
) -> int | None:
    """Save a transcription to history. Returns the new row id."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO transcriptions (text, raw_text, corrected, language, duration, mode, user_id, tenant_id, processing_ms, whisper_model) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (text, raw_text, int(corrected), language, duration, mode, user_id, tenant_id, processing_ms, whisper_model),
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


async def clear_history(tenant_id: str = "default") -> None:
    """Delete transcription history for a tenant."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM transcriptions WHERE tenant_id = ?", (tenant_id,))
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

async def get_dictionary(user_id: str, tenant_id: str = "default", include_smart: bool = False) -> list[dict]:
    """Return dictionary entries for user.

    include_smart=False (default): only manual entries (personal/team) — for UI display.
    include_smart=True: all entries including auto-generated smart dict — for pipeline use.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if include_smart:
            # Pipeline: personal + team + smart + bundle (bundle is tenant-wide)
            query = """SELECT * FROM user_dictionary
                       WHERE tenant_id = ? AND (scope IN ('team', 'bundle') OR user_id = ?)
                       ORDER BY length(trigger) DESC, trigger"""
        else:
            # UI: only personal + team (bundle hidden)
            query = """SELECT * FROM user_dictionary
                       WHERE tenant_id = ? AND (scope = 'team' OR (user_id = ? AND scope = 'personal'))
                       ORDER BY scope, trigger"""
        async with db.execute(query, (tenant_id, user_id)) as cursor:
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


async def delete_snippet(snippet_id: int, user_id: str, tenant_id: str = "default") -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM snippets WHERE id = ? AND user_id = ? AND tenant_id = ? AND scope = 'personal'",
            (snippet_id, user_id, tenant_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def delete_dictionary_entry(entry_id: int, user_id: str, tenant_id: str = "default") -> bool:
    """Delete an entry. Users can only delete their own personal entries."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM user_dictionary WHERE id = ? AND user_id = ? AND tenant_id = ? AND scope = 'personal'",
            (entry_id, user_id, tenant_id),
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


# ── Training Dataset ───────────────────────────────────────────────────────────

async def import_training_sentences(training_set: str, sentences: list[dict]) -> int:
    """Bulk import sentences if table is empty for this training_set. Returns count inserted."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM training_sentences WHERE training_set = ?", (training_set,)
        ) as cur:
            row = await cur.fetchone()
            if row[0] > 0:
                return 0  # already imported
        await db.executemany(
            "INSERT INTO training_sentences (training_set, persona, scenario, text) VALUES (?,?,?,?)",
            [(training_set, s.get("persona"), s.get("scenario"), s["text"]) for s in sentences],
        )
        await db.commit()
        return len(sentences)


async def get_random_unrecorded_sentence(training_set: str) -> dict | None:
    """Random sentence with zero recordings. Falls back to any random if all recorded."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT s.id, s.persona, s.scenario, s.text,
                      (SELECT COUNT(*) FROM training_recordings r WHERE r.sentence_id = s.id) AS take_count
               FROM training_sentences s
               WHERE s.training_set = ?
                 AND NOT EXISTS (SELECT 1 FROM training_recordings r WHERE r.sentence_id = s.id)
               ORDER BY RANDOM() LIMIT 1""",
            (training_set,),
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            # All recorded — return any random
            async with db.execute(
                "SELECT id, persona, scenario, text FROM training_sentences WHERE training_set = ? ORDER BY RANDOM() LIMIT 1",
                (training_set,),
            ) as cur:
                row = await cur.fetchone()
        if row is None:
            return None
        total = await _count_sentences(db, training_set)
        return {"id": row["id"], "persona": row["persona"], "scenario": row["scenario"], "text": row["text"], "total": total}


async def get_training_sentence_by_id(sentence_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, training_set, persona, scenario, text FROM training_sentences WHERE id = ?",
            (sentence_id,),
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            return None
        total = await _count_sentences(db, row["training_set"])
        return {"id": row["id"], "training_set": row["training_set"], "persona": row["persona"], "scenario": row["scenario"], "text": row["text"], "total": total}


async def save_training_recording(sentence_id: int, training_set: str, wav_path: str, whisper_out: str, duration_ms: int | None = None) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "INSERT INTO training_recordings (sentence_id, training_set, wav_path, whisper_out, duration_ms) VALUES (?,?,?,?,?)",
            (sentence_id, training_set, wav_path, whisper_out, duration_ms),
        ) as cur:
            row_id = cur.lastrowid
        await db.commit()
    return row_id


async def delete_training_recording(wav_path: str, tenant_id: str = "default") -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "DELETE FROM training_recordings WHERE wav_path = ? AND tenant_id = ?", (wav_path, tenant_id)
        ) as cur:
            deleted = cur.rowcount > 0
        await db.commit()
    return deleted


async def get_recordings_for_sentence(sentence_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, wav_path, whisper_out, duration_ms, created_at FROM training_recordings WHERE sentence_id = ? ORDER BY created_at",
            (sentence_id,),
        ) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def get_recorded_sentences(training_set: str) -> list[dict]:
    """All sentences that have at least one recording, with their recordings."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        total = await _count_sentences(db, training_set)
        async with db.execute(
            """SELECT DISTINCT s.id, s.persona, s.scenario, s.text
               FROM training_sentences s
               JOIN training_recordings r ON r.sentence_id = s.id
               WHERE s.training_set = ?
               ORDER BY s.id""",
            (training_set,),
        ) as cur:
            sentences = await cur.fetchall()
        result = []
        for s in sentences:
            async with db.execute(
                "SELECT wav_path, whisper_out FROM training_recordings WHERE sentence_id = ? ORDER BY created_at",
                (s["id"],),
            ) as cur:
                recs = await cur.fetchall()
            result.append({
                "id": s["id"], "persona": s["persona"], "scenario": s["scenario"],
                "text": s["text"], "total": total,
                "recordings": [{"whisper": r["whisper_out"] or "", "wav_path": r["wav_path"]} for r in recs],
            })
    return result


async def _count_sentences(db, training_set: str) -> int:
    async with db.execute(
        "SELECT COUNT(*) FROM training_sentences WHERE training_set = ?", (training_set,)
    ) as cur:
        row = await cur.fetchone()
    return row[0] or 0


# ------------------------------------------------------------------
# Symbol Index V2
# ------------------------------------------------------------------

# ------------------------------------------------------------------
# Bundle dictionary
# ------------------------------------------------------------------

async def load_bundle_entries(tenant_id: str, entries: list[dict]) -> int:
    """Replace bundle-scope dictionary entries for a tenant. Returns count inserted."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM user_dictionary WHERE tenant_id = ? AND scope = 'bundle'", (tenant_id,)
        )
        await db.executemany(
            "INSERT OR IGNORE INTO user_dictionary (tenant_id, user_id, trigger, replacement, scope) VALUES (?, ?, ?, ?, 'bundle')",
            [(tenant_id, "", e["trigger"], e["replacement"]) for e in entries],
        )
        await db.commit()
    return len(entries)


async def clear_bundle_entries(tenant_id: str) -> None:
    """Remove all bundle-scope dictionary entries for a tenant."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM user_dictionary WHERE tenant_id = ? AND scope = 'bundle'", (tenant_id,)
        )
        await db.commit()


# ------------------------------------------------------------------
# Context / smart dictionary status
# ------------------------------------------------------------------

async def get_context_status(user_id: str) -> dict:
    """Return smart dictionary + symbol index counts for a user."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM user_dictionary WHERE user_id = ? AND scope = 'smart'", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            n = row[0] if row else 0
        async with db.execute(
            "SELECT COUNT(*), MAX(indexed_at) FROM symbol_index_v2 WHERE user_id = ?", (user_id,)
        ) as cursor:
            row2 = await cursor.fetchone()
            sym_count = row2[0] if row2 else 0
            last_indexed_at = row2[1] if row2 else None
    return {"smart_count": n, "symbol_count": sym_count, "last_indexed_at": last_indexed_at}


async def get_context_projects(user_id: str) -> dict:
    """Return indexed projects with symbol counts and smart dictionary word count."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT project_path, COUNT(*) FROM symbol_index WHERE user_id = ? GROUP BY project_path",
            (user_id,),
        ) as cursor:
            symbol_rows = {row[0]: row[1] for row in await cursor.fetchall()}
        async with db.execute(
            "SELECT COUNT(*) FROM user_dictionary WHERE user_id = ? AND scope = 'smart'", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            smart_total = row[0] if row else 0
    return {"symbol_rows": symbol_rows, "smart_total": smart_total}


async def clear_smart_dictionary(user_id: str, tenant_id: str = "default") -> None:
    """Remove smart-scope dictionary entries for a user."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM user_dictionary WHERE user_id = ? AND tenant_id = ? AND scope = 'smart'",
            (user_id, tenant_id),
        )
        await db.commit()


# ------------------------------------------------------------------
# Smart dictionary bulk ops
# ------------------------------------------------------------------

async def get_dictionary_triggers(user_id: str) -> set[str]:
    """Return all existing trigger strings for a user (for dedup checks)."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT trigger FROM user_dictionary WHERE user_id = ?", (user_id,)
        ) as cursor:
            return {row[0] for row in await cursor.fetchall()}


async def bulk_add_smart_entries(
    user_id: str, tenant_id: str, pairs: list[tuple[str, str]]
) -> int:
    """Insert (trigger, replacement) pairs with scope=smart. Skips existing triggers. Returns added count."""
    existing = await get_dictionary_triggers(user_id)
    to_insert = [
        (tenant_id, user_id, trigger, replacement, "smart")
        for trigger, replacement in pairs
        if trigger and replacement and trigger not in existing
    ]
    if not to_insert:
        return 0
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executemany(
            "INSERT INTO user_dictionary (tenant_id, user_id, trigger, replacement, scope) VALUES (?, ?, ?, ?, ?)",
            to_insert,
        )
        await db.commit()
    return len(to_insert)


# ------------------------------------------------------------------
# Symbol index DB ops (used by symbol/ package)
# ------------------------------------------------------------------

async def clear_symbol_indexes(user_id: str, project_path: str) -> None:
    """Clear both symbol_index and symbol_index_v2 for a user+project."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM symbol_index_v2 WHERE user_id = ? AND project_path = ?",
            (user_id, project_path),
        )
        await db.execute(
            "DELETE FROM symbol_index WHERE user_id = ? AND project_path = ?",
            (user_id, project_path),
        )
        await db.commit()


async def save_symbol_batch(
    user_id: str,
    project_path: str,
    symbols: list,  # list[SymbolInfo] — avoid circular import
) -> None:
    """Bulk insert symbols into symbol_index_v2 and symbol_index (compat)."""
    import json
    async with aiosqlite.connect(DB_PATH) as db:
        for sym in symbols:
            await db.execute(
                """INSERT INTO symbol_index_v2
                   (user_id, project_path, file_path, symbol_type, symbol_name,
                    line_number, end_line, signature, parent_symbol, parent_class,
                    conformances, return_type, properties, imports, decorators,
                    visibility, is_static)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    user_id, project_path, sym.file_path, sym.symbol_type, sym.symbol_name,
                    sym.line_number, sym.end_line, sym.signature, sym.parent_symbol,
                    sym.parent_class, sym.conformances, sym.return_type,
                    json.dumps(sym.properties, ensure_ascii=False) if sym.properties else None,
                    json.dumps(sym.imports, ensure_ascii=False) if sym.imports else None,
                    json.dumps(sym.decorators, ensure_ascii=False) if sym.decorators else None,
                    sym.visibility, int(sym.is_static),
                ),
            )
            await db.execute(
                """INSERT OR IGNORE INTO symbol_index
                   (user_id, project_path, file_path, symbol_type, symbol_name, line_number)
                   VALUES (?,?,?,?,?,?)""",
                (user_id, project_path, sym.file_path, sym.symbol_type, sym.symbol_name, sym.line_number),
            )
        await db.commit()


async def get_symbol_index_file_paths(user_id: str) -> list[dict]:
    """Return (project_path, file_path) rows from symbol_index for a user."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT DISTINCT project_path, file_path FROM symbol_index WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            return [dict(r) for r in await cursor.fetchall()]


async def get_symbols_for_matching(
    user_id: str,
    symbol_types: tuple[str, ...] = ("class", "struct", "protocol", "enum", "interface", "object", "module"),
) -> list[dict]:
    """Return symbols from symbol_index for fuzzy/phonetic matching."""
    placeholders = ",".join("?" * len(symbol_types))
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            f"""SELECT symbol_name, file_path, line_number, symbol_type
                FROM symbol_index WHERE user_id = ?
                AND symbol_type IN ({placeholders})""",
            (user_id, *symbol_types),
        ) as cursor:
            return [dict(r) for r in await cursor.fetchall()]


async def lookup_symbol_exact(query: str, user_id: str, limit: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT symbol_name, symbol_type, file_path, line_number,
                      end_line, signature, parent_symbol, parent_class,
                      conformances, return_type
               FROM symbol_index_v2
               WHERE user_id = ? AND LOWER(symbol_name) = LOWER(?)
               ORDER BY CASE symbol_type WHEN 'class' THEN 0 WHEN 'struct' THEN 1 WHEN 'protocol' THEN 2 ELSE 3 END
               LIMIT ?""",
            (user_id, query, limit),
        ) as cursor:
            return [dict(r) for r in await cursor.fetchall()]


async def lookup_symbol_prefix(query: str, user_id: str, limit: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT symbol_name, symbol_type, file_path, line_number,
                      end_line, signature, parent_symbol, parent_class,
                      conformances, return_type
               FROM symbol_index_v2
               WHERE user_id = ? AND LOWER(symbol_name) LIKE LOWER(?)
               ORDER BY length(symbol_name) LIMIT ?""",
            (user_id, f"{query}%", limit),
        ) as cursor:
            return [dict(r) for r in await cursor.fetchall()]


async def lookup_symbol_substring(query: str, user_id: str, limit: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT symbol_name, symbol_type, file_path, line_number,
                      end_line, signature, parent_symbol, parent_class,
                      conformances, return_type
               FROM symbol_index_v2
               WHERE user_id = ? AND LOWER(symbol_name) LIKE LOWER(?)
               ORDER BY length(symbol_name) LIMIT ?""",
            (user_id, f"%{query}%", limit),
        ) as cursor:
            return [dict(r) for r in await cursor.fetchall()]


async def get_symbols_for_notes(user_id: str, project_path: str) -> list[dict]:
    """Fetch enriched symbols for project-notes generation."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT symbol_type, symbol_name, file_path, line_number,
                      parent_class, conformances, signature, imports
               FROM symbol_index_v2
               WHERE user_id = ? AND project_path = ?
               ORDER BY symbol_type, symbol_name""",
            (user_id, project_path),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def clear_symbol_index_v2(user_id: str, project_path: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM symbol_index_v2 WHERE user_id = ? AND project_path = ?",
            (user_id, project_path),
        )
        await db.commit()


# ------------------------------------------------------------------
# Token Blacklist (JWT revocation)
# ------------------------------------------------------------------

async def revoke_token(jti: str, expires_at: str) -> None:
    """Add token JTI to blacklist. expires_at is ISO 8601 UTC string."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO token_blacklist (jti, expires_at) VALUES (?, ?)",
            (jti, expires_at),
        )
        await db.commit()


async def is_token_revoked(jti: str) -> bool:
    """Return True if token JTI is in the blacklist."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM token_blacklist WHERE jti = ?", (jti,)
        ) as cursor:
            return (await cursor.fetchone()) is not None


async def purge_expired_tokens() -> int:
    """Delete blacklist entries whose JWT has already expired. Returns count."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM token_blacklist WHERE expires_at < datetime('now')"
        )
        await db.commit()
        return cursor.rowcount
