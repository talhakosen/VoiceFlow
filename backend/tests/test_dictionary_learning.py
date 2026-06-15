"""Unit tests for background dictionary learning.

Covers the quality guards (parse, phonetic, hallucination/frequency) and the
orchestrator wiring with the DB + LLM mocked — no model load, no real DB.
"""

import asyncio

from voiceflow.services import dictionary_learning as dl


class TestExtractPairs:
    def test_plain_json_array(self):
        out = dl.extract_pairs('[{"wrong": "diploy", "correct": "deploy"}]')
        assert out == [("diploy", "deploy")]

    def test_json_wrapped_in_prose(self):
        raw = 'Sure! Here are the pairs:\n[{"wrong": "komut", "correct": "commit"}]\nDone.'
        assert dl.extract_pairs(raw) == [("komut", "commit")]

    def test_invalid_json_returns_empty(self):
        assert dl.extract_pairs("not json at all") == []
        assert dl.extract_pairs("[broken") == []

    def test_skips_non_dict_and_equal_pairs(self):
        raw = '["junk", {"wrong": "x", "correct": "x"}, {"wrong": "brençh", "correct": "branch"}]'
        assert dl.extract_pairs(raw) == [("brençh", "branch")]

    def test_empty_array(self):
        assert dl.extract_pairs("[]") == []


class TestPhonetic:
    def test_close_misrecognition_passes(self):
        assert dl.phonetically_similar("diploy", "deploy") is True
        assert dl.phonetically_similar("brençh", "branch") is True

    def test_unrelated_words_fail(self):
        assert dl.phonetically_similar("deploy", "banana") is False

    def test_semantic_rewrite_fails(self):
        # Same meaning, different sound — NOT an STT error, must be rejected.
        assert dl.phonetically_similar("araba", "otomobil") is False

    def test_empty_fails(self):
        assert dl.phonetically_similar("", "deploy") is False


class TestFilterPairs:
    def test_happy_path(self):
        texts = ["kodu diploy ettim", "tekrar diploy lazım"]
        pairs = [("diploy", "deploy")]
        assert dl.filter_pairs(pairs, texts, min_freq=2) == [("diploy", "deploy")]

    def test_hallucination_guard_drops_unseen_word(self):
        # LLM proposes a word that never appears in the texts → dropped.
        texts = ["merhaba dünya"]
        assert dl.filter_pairs([("diploy", "deploy")], texts, min_freq=1) == []

    def test_frequency_guard(self):
        texts = ["sadece bir kez diploy"]
        assert dl.filter_pairs([("diploy", "deploy")], texts, min_freq=2) == []
        assert dl.filter_pairs([("diploy", "deploy")], texts, min_freq=1) == [("diploy", "deploy")]

    def test_phonetic_guard_drops_semantic(self):
        texts = ["araba araba"]
        assert dl.filter_pairs([("araba", "otomobil")], texts, min_freq=1) == []

    def test_dedup_by_trigger_lowercased(self):
        texts = ["Diploy diploy DIPLOY"]
        pairs = [("Diploy", "deploy"), ("diploy", "deploy")]
        out = dl.filter_pairs(pairs, texts, min_freq=2)
        assert out == [("diploy", "deploy")]  # single lower-cased trigger


# ---------------------------------------------------------------------------
# Orchestrator — DB + LLM mocked
# ---------------------------------------------------------------------------

class _FakeCorrector:
    def __init__(self, output):
        self._output = output

    def complete(self, system, user, max_tokens=256):
        return self._output


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


class TestLearnFromHistory:
    def test_adds_filtered_pairs(self, monkeypatch):
        rows = [
            {"raw_text": "kodu diploy ettim sonra"},
            {"raw_text": "tekrar diploy yaptım"},
            {"raw_text": "bir de komut attım"},
            {"raw_text": "yine komut lazım"},
        ]
        captured = {}

        async def fake_get_history(limit, user_id, tenant_id):
            return rows

        async def fake_bulk_add(user_id, tenant_id, pairs):
            captured["pairs"] = pairs
            return len(pairs)

        monkeypatch.setattr(dl, "get_history", fake_get_history)
        monkeypatch.setattr(dl, "bulk_add_smart_entries", fake_bulk_add)

        corrector = _FakeCorrector(
            '[{"wrong": "diploy", "correct": "deploy"}, '
            '{"wrong": "komut", "correct": "commit"}]'
        )
        added = _run(dl.learn_from_history("u1", "default", corrector, None, min_freq=2))

        assert added == 2
        assert ("diploy", "deploy") in captured["pairs"]
        assert ("komut", "commit") in captured["pairs"]

    def test_noop_without_complete(self, monkeypatch):
        called = {"hist": False}

        async def fake_get_history(limit, user_id, tenant_id):
            called["hist"] = True
            return []

        monkeypatch.setattr(dl, "get_history", fake_get_history)
        added = _run(dl.learn_from_history("u1", "default", object(), None))

        assert added == 0
        assert called["hist"] is False  # bailed before touching the DB

    def test_noop_on_empty_history(self, monkeypatch):
        async def fake_get_history(limit, user_id, tenant_id):
            return []

        monkeypatch.setattr(dl, "get_history", fake_get_history)
        added = _run(dl.learn_from_history("u1", "default", _FakeCorrector("[]"), None))
        assert added == 0
