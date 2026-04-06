"""Tests for the isolated_db fixture and DB isolation guarantee."""

import asyncio
import pytest


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestIsolatedDbFixture:
    """Verify isolated_db gives a clean, migrated DB per test."""

    def test_tables_created(self, isolated_db, db_conn):
        """init_db() created all expected tables."""
        tables = {r[0] for r in db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        assert "transcriptions" in tables
        assert "user_dictionary" in tables
        assert "snippets" in tables
        assert "token_blacklist" in tables

    def test_db_starts_empty(self, isolated_db, db_conn):
        """New isolated_db has zero transcriptions."""
        count = db_conn.execute("SELECT COUNT(*) FROM transcriptions").fetchone()[0]
        assert count == 0

    def test_write_and_read(self, isolated_db):
        """save_transcription + get_history round-trip."""
        from voiceflow.db import save_transcription, get_history

        async def _run():
            row_id = await save_transcription(
                text="Merhaba dünya",
                raw_text="merhaba dunya",
                corrected=True,
                user_id="u1",
                tenant_id="test",
            )
            assert isinstance(row_id, int) and row_id > 0

            rows = await get_history(limit=10, offset=0, tenant_id="test")
            assert len(rows) == 1
            assert rows[0]["text"] == "Merhaba dünya"

        run(_run())

    def test_isolation_between_tests_a(self, isolated_db, db_conn):
        """First test writes data — should not appear in test_isolation_between_tests_b."""
        from voiceflow.db import save_transcription

        async def _run():
            await save_transcription(
                text="Only in test A",
                raw_text="only in test a",
                corrected=False,
                user_id="u1",
                tenant_id="test",
            )

        run(_run())
        count = db_conn.execute("SELECT COUNT(*) FROM transcriptions").fetchone()[0]
        assert count == 1

    def test_isolation_between_tests_b(self, isolated_db, db_conn):
        """Second test — DB is fresh, no data from test A."""
        count = db_conn.execute("SELECT COUNT(*) FROM transcriptions").fetchone()[0]
        assert count == 0


class TestDeleteTranscriptionById:
    """Tests for delete_transcription_by_id()."""

    def test_delete_existing_row(self, isolated_db):
        from voiceflow.db import save_transcription, get_history
        from voiceflow.db.transcription_storage import delete_transcription_by_id

        async def _run():
            row_id = await save_transcription(
                text="Silinecek kayıt", tenant_id="test"
            )
            deleted = await delete_transcription_by_id(row_id, tenant_id="test")
            assert deleted is True
            rows = await get_history(tenant_id="test")
            assert len(rows) == 0

        run(_run())

    def test_delete_nonexistent_row(self, isolated_db):
        from voiceflow.db.transcription_storage import delete_transcription_by_id

        async def _run():
            deleted = await delete_transcription_by_id(9999, tenant_id="test")
            assert deleted is False

        run(_run())

    def test_delete_wrong_tenant(self, isolated_db):
        """Cannot delete a row belonging to another tenant."""
        from voiceflow.db import save_transcription, get_history
        from voiceflow.db.transcription_storage import delete_transcription_by_id

        async def _run():
            row_id = await save_transcription(
                text="Başka tenant kaydı", tenant_id="tenant_a"
            )
            deleted = await delete_transcription_by_id(row_id, tenant_id="tenant_b")
            assert deleted is False
            rows = await get_history(tenant_id="tenant_a")
            assert len(rows) == 1

        run(_run())
