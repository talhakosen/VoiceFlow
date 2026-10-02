"""Learned dictionary entries: visible in the UI, removable, never re-learned.

Öğrenme yanlış bir ikame ekleyebilir; kullanıcının Ayarlar'da görüp silebilmesi
güvenlik ağı. Silinen kayıt "rejected" olarak kalır: diktede uygulanmaz, ama
bir sonraki öğrenme aynı yanlışı tekrar eklemesin diye tetikleyici hatırlanır.
"""

import asyncio
import sqlite3

import pytest

from voiceflow.db import dictionary_storage as ds
from voiceflow.services.dictionary_service import list_dictionary, remove_dictionary_entry


def run(coro):
    return asyncio.run(coro)


def scopes():
    db = sqlite3.connect(ds.DB_PATH)
    rows = dict(db.execute("SELECT trigger, scope FROM user_dictionary").fetchall())
    db.close()
    return rows


@pytest.fixture(autouse=True)
def clean_cache():
    ds.invalidate_dictionary_cache()
    yield
    ds.invalidate_dictionary_cache()


@pytest.fixture
def learned(isolated_db):
    run(ds.bulk_add_smart_entries("u1", "default", [("diploy", "deploy")], scope="learned"))
    db = sqlite3.connect(ds.DB_PATH)
    entry_id = db.execute("SELECT id FROM user_dictionary WHERE trigger = 'diploy'").fetchone()[0]
    db.close()
    return entry_id


def test_learned_entries_are_listed_for_the_ui(learned):
    run(ds.bulk_add_smart_entries("u1", "default", [("reposteri", "Repository")]))  # indeksleme
    items = run(list_dictionary("u1"))["items"]
    assert [(e["trigger"], e["scope"]) for e in items] == [("diploy", "learned")]


def test_learned_entries_are_applied(learned):
    entries = run(ds.get_dictionary("u1", include_smart=True))
    assert ("diploy", "deploy") in {(e["trigger"], e["replacement"]) for e in entries}


def test_removing_learned_entry_rejects_it(learned):
    run(remove_dictionary_entry(learned, "u1"))
    assert scopes() == {"diploy": "rejected"}


def test_rejected_entry_is_not_applied_or_listed(learned):
    run(remove_dictionary_entry(learned, "u1"))
    applied = run(ds.get_dictionary("u1", include_smart=True))
    listed = run(list_dictionary("u1"))["items"]
    assert not any(e["trigger"] == "diploy" for e in applied + listed)


def test_rejected_entry_is_never_relearned(learned):
    run(remove_dictionary_entry(learned, "u1"))
    added = run(ds.bulk_add_smart_entries("u1", "default", [("diploy", "deploy")], scope="learned"))
    assert added == 0
    assert scopes() == {"diploy": "rejected"}


def test_cannot_remove_other_users_learned_entry(learned):
    with pytest.raises(LookupError):
        run(remove_dictionary_entry(learned, "someone-else"))
    assert scopes() == {"diploy": "learned"}


def test_personal_entries_are_still_deleted(isolated_db):
    entry_id = run(ds.add_dictionary_entry("vf", "VoiceFlow", user_id="u1"))
    run(remove_dictionary_entry(entry_id, "u1"))
    assert scopes() == {}


def test_purge_covers_learned_scope(isolated_db):
    db = sqlite3.connect(ds.DB_PATH)
    db.execute("INSERT INTO user_dictionary (tenant_id, user_id, trigger, replacement, scope) "
               "VALUES ('default', 'u1', 'komut', 'commit', 'learned')")
    db.commit(); db.close()
    assert run(ds.purge_turkish_word_entries()) == 1
