"""Database initialization and schema migrations."""

import logging

from ._base import aiosqlite, DB_PATH

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

        # ── Migrations ────────────────────────────────────────────────────────
        async with db.execute("PRAGMA table_info(transcriptions)") as cursor:
            columns = {row[1] async for row in cursor}
        for col, ddl in [
            ("user_id", "ALTER TABLE transcriptions ADD COLUMN user_id TEXT"),
            ("tenant_id", "ALTER TABLE transcriptions ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'default'"),
            ("processing_ms", "ALTER TABLE transcriptions ADD COLUMN processing_ms INTEGER"),
            ("whisper_model", "ALTER TABLE transcriptions ADD COLUMN whisper_model TEXT"),
            ("corrections", "ALTER TABLE transcriptions ADD COLUMN corrections TEXT"),
        ]:
            if col not in columns:
                await db.execute(ddl)
                logger.info("Migration: added %s column to transcriptions", col)

        async with db.execute("PRAGMA table_info(users)") as cursor:
            user_columns = {row[1] async for row in cursor}
        if "is_active" not in user_columns:
            await db.execute("ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
            logger.info("Migration: added is_active column to users")

        for table in ("training_sentences", "training_recordings", "symbol_index", "symbol_index_v2"):
            async with db.execute(f"PRAGMA table_info({table})") as cursor:  # noqa: S608
                cols = {row[1] async for row in cursor}
            if "tenant_id" not in cols:
                await db.execute(f"ALTER TABLE {table} ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'default'")  # noqa: S608
                logger.info("Migration: added tenant_id to %s", table)

        await db.commit()
    logger.info("Database initialized at %s", DB_PATH)
