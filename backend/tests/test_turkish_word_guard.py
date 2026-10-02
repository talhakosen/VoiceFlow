"""Auto-generated dictionary entries must never rewrite real Turkish words.

Regresyon (2026-10-01): IT bundle generator'ı kısa terimlere Türkçe ek
ekleyerek varyant üretiyordu (di+ye → "diye → DI'ye", dos+ya → "dosya → DoS'ya"),
kod indeksleme de identifier'ları Türkçeye çevirip tersini yazıyordu
("ekran → Screen", "hata → Exception"). Sözlük her diktede, correction kapalıyken
bile uygulandığı için 336 diktenin 302'si bozulmuştu.

Manuel (personal/team) kayıtlar korumanın dışında — kullanıcı bilerek ekledi.
"""

import asyncio

import pytest

from voiceflow.core.turkish_words import is_turkish_phrase, without_turkish_triggers
from voiceflow.db import dictionary_storage as ds


class TestIsTurkishPhrase:
    @pytest.mark.parametrize("trigger", ["diye", "bunları", "ekran", "Ürün", "HATA", "İşte", "alt"])
    def test_common_turkish_words(self, trigger):
        assert is_turkish_phrase(trigger)

    @pytest.mark.parametrize("trigger", [
        "komit", "kron", "reposteri", "diploy", "midılveyr",
        "paste servis",  # bir kelime Türkçe değil → ifade Türkçe değil
        "", "  ",
    ])
    def test_misheard_terms_are_not_turkish(self, trigger):
        assert not is_turkish_phrase(trigger)

    def test_all_words_must_be_turkish(self):
        assert is_turkish_phrase("yeni ekran")

    @pytest.mark.parametrize("trigger", ["şifreyi", "panelde", "kütüphaneler", "ekranları"])
    def test_inflected_turkish_words(self, trigger):
        # Türkçe kök + ek: listede çekimli hali olmasa da kök varsa Türkçe
        assert is_turkish_phrase(trigger)

    @pytest.mark.parametrize("trigger", ["buton", "butonu", "butona", "veritabanı"])
    def test_tech_turkish_words_missing_from_news_corpus(self, trigger):
        # ISSAI haber dili — teknik bağlamdaki Türkçe kelimeler elle eklenen listede
        assert is_turkish_phrase(trigger)

    @pytest.mark.parametrize("trigger", ["klasları", "indeksin", "view model", "reposteri", "komponent"])
    def test_stem_rule_keeps_misheard_terms(self, trigger):
        # kök Türkçe değilse ek almış olması onu Türkçe yapmaz
        assert not is_turkish_phrase(trigger)


class TestWithoutTurkishTriggers:
    def test_drops_turkish_keeps_rest(self):
        pairs = [("ekran", "Screen"), ("komit", "commit"), ("diye", "DI'ye")]
        assert without_turkish_triggers(pairs) == [("komit", "commit")]

    def test_keeps_identity_entries(self):
        # "log → log" changes nothing; dropping it would be pointless churn
        assert without_turkish_triggers([("alt", "Alt")]) == [("alt", "Alt")]


def _rows(scope=None):
    import sqlite3
    db = sqlite3.connect(ds.DB_PATH)
    q = "SELECT trigger, scope FROM user_dictionary" + (" WHERE scope = ?" if scope else "")
    rows = db.execute(q, (scope,) if scope else ()).fetchall()
    db.close()
    return {t for t, _ in rows}


class TestStorageGuard:
    def test_bundle_load_skips_turkish_triggers(self, isolated_db):
        n = asyncio.run(ds.load_bundle_entries("default", [
            {"trigger": "diye", "replacement": "DI'ye"},
            {"trigger": "komit", "replacement": "commit"},
        ]))
        assert n == 1
        assert _rows("bundle") == {"komit"}

    def test_smart_add_skips_turkish_triggers(self, isolated_db):
        n = asyncio.run(ds.bulk_add_smart_entries("u1", "default", [
            ("ekran", "Screen"), ("reposteri", "Repository"),
        ]))
        assert n == 1
        assert _rows("smart") == {"reposteri"}

    def test_manual_entries_untouched(self, isolated_db):
        asyncio.run(ds.add_dictionary_entry(
            user_id="u1", trigger="ekran", replacement="Screen", scope="personal"))
        assert _rows("personal") == {"ekran"}

    def test_purge_removes_existing_bad_rows_only(self, isolated_db):
        import sqlite3
        db = sqlite3.connect(ds.DB_PATH)
        db.executemany(
            "INSERT INTO user_dictionary (tenant_id, user_id, trigger, replacement, scope) VALUES ('default', ?, ?, ?, ?)",
            [("", "diye", "DI'ye", "bundle"), ("", "komit", "commit", "bundle"),
             ("u1", "ekran", "Screen", "smart"), ("u1", "ekran", "Screen", "personal")],
        )
        db.commit(); db.close()

        removed = asyncio.run(ds.purge_turkish_word_entries())

        assert removed == 2
        assert _rows("bundle") == {"komit"}
        assert _rows("smart") == set()
        assert _rows("personal") == {"ekran"}

    def test_purge_invalidates_cache(self, isolated_db):
        v = ds.dictionary_version()
        import sqlite3
        db = sqlite3.connect(ds.DB_PATH)
        db.execute("INSERT INTO user_dictionary (tenant_id, user_id, trigger, replacement, scope) "
                   "VALUES ('default', '', 'diye', 'DI''ye', 'bundle')")
        db.commit(); db.close()
        asyncio.run(ds.purge_turkish_word_entries())
        assert ds.dictionary_version() != v
