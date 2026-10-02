"""Shared pytest fixtures for VoiceFlow backend tests.

The key fixture here is `isolated_db`, which gives each test an empty,
fully-migrated SQLite database in a temp file — no cross-test pollution.
"""

import asyncio
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """Provide an isolated, fully-migrated SQLite DB for a single test.

    Usage:
        def test_something(isolated_db):
            # DB_PATH in all db modules is patched to isolated_db
            ...

    Implementation:
        - Creates a temp SQLite file
        - Patches DB_PATH across all storage modules
        - Runs init_db() synchronously to create all tables
        - Cleans up automatically via tmp_path
    """
    db_file = tmp_path / "test_voiceflow.db"
    db_str = db_file  # keep as Path — migrations.py uses .parent.mkdir()

    # Also ensure no encryption in tests
    monkeypatch.setenv("DB_ENCRYPTION_KEY", "")

    # Import modules first, then patch their DB_PATH binding
    import voiceflow.db._base as _base
    import voiceflow.db.transcription_storage as _ts
    import voiceflow.db.config_storage as _cs
    import voiceflow.db.dictionary_storage as _ds
    import voiceflow.db.user_storage as _us
    import voiceflow.db.audit_storage as _as
    import voiceflow.db.token_storage as _tks
    import voiceflow.db.migrations as _mg

    for mod in (_base, _ts, _cs, _ds, _us, _as, _tks, _mg):
        monkeypatch.setattr(mod, "DB_PATH", db_str, raising=False)

    # Run migrations to create all tables
    from voiceflow.db.migrations import init_db
    loop = asyncio.new_event_loop()
    loop.run_until_complete(init_db())
    loop.close()

    yield db_file

    # tmp_path cleanup is automatic


@pytest.fixture
def db_conn(isolated_db):
    """Synchronous sqlite3 connection for assertion queries in tests.

    Usage:
        def test_something(isolated_db, db_conn):
            rows = db_conn.execute("SELECT * FROM transcriptions").fetchall()
    """
    conn = sqlite3.connect(str(isolated_db))
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()
