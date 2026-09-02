"""Sözlük cache'i — okuma cache'lenir, HER yazma geçersiz kılar.

Regresyon: sözlük her diktede DB'den okunuyordu. include_smart=True 78.107
kayıt döndürüyor ve 285ms sürüyordu — metin işleme aşamasının tamamı
(ölçüldü 2026-09-02, M4). Sözlük ise nadiren değişiyor.

Buradaki asıl risk hız değil DOĞRULUK: cache geçersiz kılınmazsa kullanıcı
eklediği kelimenin çalışmadığını görür. O yüzden testlerin çoğu invalidation.
"""

import asyncio
import inspect

import pytest

from voiceflow.db import dictionary_storage as ds


def read(user_id: str, tenant_id: str = "default", include_smart: bool = True):
    return asyncio.run(
        ds.get_dictionary(user_id=user_id, tenant_id=tenant_id, include_smart=include_smart)
    )


@pytest.fixture(autouse=True)
def clean_cache():
    ds.invalidate_dictionary_cache()
    yield
    ds.invalidate_dictionary_cache()


@pytest.fixture
def db_reads(monkeypatch):
    """get_dictionary'nin DB'ye kaç kez gittiğini sayar."""
    calls = {"n": 0}
    rows = [{"id": 1, "trigger": "vf", "replacement": "VoiceFlow", "scope": "personal"}]

    class FakeCursor:
        async def fetchall(self):
            return rows

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    class FakeDB:
        row_factory = None

        def execute(self, *a, **k):
            calls["n"] += 1
            return FakeCursor()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    monkeypatch.setattr(ds.aiosqlite, "connect", lambda *a, **k: FakeDB())
    return calls


class TestCaching:
    def test_second_read_does_not_hit_db(self, db_reads):
        read("u1")
        read("u1")
        read("u1")
        assert db_reads["n"] == 1

    def test_include_smart_is_a_separate_key(self, db_reads):
        # Pipeline (smart=True) ve UI (smart=False) farklı sorgular — karışmamalı
        read("u1", include_smart=True)
        read("u1", include_smart=False)
        assert db_reads["n"] == 2

    def test_different_users_are_isolated(self, db_reads):
        read("u1")
        read("u2")
        assert db_reads["n"] == 2

    def test_different_tenants_are_isolated(self, db_reads):
        read("u1", tenant_id="a")
        read("u1", tenant_id="b")
        assert db_reads["n"] == 2

    def test_cache_is_bounded(self, db_reads):
        for i in range(ds._MAX_CACHED_KEYS + 4):
            read(f"u{i}")
        assert len(ds._cache) <= ds._MAX_CACHED_KEYS


class TestInvalidation:
    def test_invalidate_forces_reread(self, db_reads):
        read("u1")
        ds.invalidate_dictionary_cache()
        read("u1")
        assert db_reads["n"] == 2

    def test_version_increments_on_every_invalidation(self):
        v0 = ds.dictionary_version()
        ds.invalidate_dictionary_cache()
        ds.invalidate_dictionary_cache()
        assert ds.dictionary_version() == v0 + 2

    @pytest.mark.parametrize("fn_name", [
        "add_dictionary_entry",
        "delete_dictionary_entry",
        "load_bundle_entries",
        "clear_bundle_entries",
        "clear_smart_dictionary",
        "bulk_add_smart_entries",
    ])
    def test_every_writer_invalidates(self, fn_name):
        """Sözlüğü değiştiren her fonksiyon cache'i geçersiz kılmalı.

        Yeni bir yazma fonksiyonu eklenip invalidation unutulursa kullanıcı
        eklediği kelimenin çalışmadığını görür — bu test onu yakalar.
        """
        src = inspect.getsource(getattr(ds, fn_name))
        assert "invalidate_dictionary_cache()" in src, (
            f"{fn_name} sözlüğü değiştiriyor ama cache'i geçersiz kılmıyor"
        )

    def test_kvkk_delete_invalidates(self):
        from voiceflow.db import audit_storage

        src = inspect.getsource(audit_storage.delete_user_data)
        assert "invalidate_dictionary_cache" in src


class TestAutomatonVersioning:
    def test_pipeline_rebuilds_on_version_change_not_entry_count(self):
        """Automaton SÜRÜMe bağlı olmalı, kayıt SAYISINA değil.

        Eskiden sayıya bakıyordu: bir kelime silinip başkası eklendiğinde
        sayı sabit kalıyor ve automaton bayat kalıyordu.
        """
        from voiceflow.recording import service

        src = inspect.getsource(service.RecordingService._apply_text_pipeline)
        assert "dictionary_version()" in src
        assert "_dict_entry_count" not in src


class TestSharedListContract:
    def test_returns_same_object_not_a_copy(self, db_reads):
        """78K kaydı her çağrıda kopyalamak cache'in amacını yok eder.

        Dönen liste paylaşılır — bu bilinçli. Test, birinin ileride
        'güvenli olsun' diye copy() eklemesini yakalar.
        """
        assert read("u1") is read("u1")
