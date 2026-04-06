"""Unit tests for pipeline corrections tracking.

Tests verify that substitutions made by dictionary, snippet, symbol, and LLM
correction steps are correctly captured in the `corrections` dict, which is
persisted to `transcriptions.corrections` (JSON) for eval.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def entry(trigger: str, replacement: str) -> dict:
    return {"trigger": trigger, "replacement": replacement, "scope": "personal"}


def snippet(trigger: str, expansion: str) -> dict:
    return {"trigger_phrase": trigger, "expansion": expansion, "scope": "personal"}


# ---------------------------------------------------------------------------
# 1. Dictionary substitution tracking
# ---------------------------------------------------------------------------

class TestDictSubstitutionTracking:
    def test_single_substitution_captured(self):
        from voiceflow.services.dictionary import _apply_aho_corasick, _build_automaton
        entries = [entry("visspar", "Whisper")]
        automaton = _build_automaton(entries)
        subs: dict[str, str] = {}
        result = _apply_aho_corasick("visspar ile konuştum", automaton, subs)
        assert result == "Whisper ile konuştum"
        assert subs == {"visspar": "Whisper"}

    def test_multi_word_substitution_captured(self):
        from voiceflow.services.dictionary import _apply_aho_corasick, _build_automaton
        entries = [entry("ant row pick", "Anthropic")]
        automaton = _build_automaton(entries)
        subs: dict[str, str] = {}
        result = _apply_aho_corasick("ant row pick modeli", automaton, subs)
        assert result == "Anthropic modeli"
        assert subs == {"ant row pick": "Anthropic"}

    def test_multiple_substitutions_captured(self):
        from voiceflow.services.dictionary import _apply_aho_corasick, _build_automaton
        entries = [entry("visspar", "Whisper"), entry("ant row pick", "Anthropic")]
        automaton = _build_automaton(entries)
        subs: dict[str, str] = {}
        _apply_aho_corasick("visspar ant row pick", automaton, subs)
        assert "visspar" in subs
        assert "ant row pick" in subs

    def test_no_match_empty_subs(self):
        from voiceflow.services.dictionary import _apply_aho_corasick, _build_automaton
        entries = [entry("visspar", "Whisper")]
        automaton = _build_automaton(entries)
        subs: dict[str, str] = {}
        result = _apply_aho_corasick("hiçbir eşleşme yok", automaton, subs)
        assert result == "hiçbir eşleşme yok"
        assert subs == {}

    def test_subs_none_does_not_crash(self):
        from voiceflow.services.dictionary import _apply_aho_corasick, _build_automaton
        entries = [entry("test", "TEST")]
        automaton = _build_automaton(entries)
        result = _apply_aho_corasick("test metni", automaton, None)
        assert result == "TEST metni"

    def test_case_insensitive_original_preserved_in_subs(self):
        from voiceflow.services.dictionary import _apply_aho_corasick, _build_automaton
        entries = [entry("visspar", "Whisper")]
        automaton = _build_automaton(entries)
        subs: dict[str, str] = {}
        _apply_aho_corasick("Visspar kullandım", automaton, subs)
        # Original casing from text should be preserved as key
        assert "Whisper" in subs.values()

    def test_regex_fallback_tracking(self):
        from voiceflow.services.dictionary import _apply_regex_fallback
        entries = [entry("visspar", "Whisper")]
        subs: dict[str, str] = {}
        result = _apply_regex_fallback("visspar sessiz", entries, subs)
        assert result == "Whisper sessiz"
        assert "visspar" in subs or "Whisper" in subs.values()

    def test_empty_automaton_returns_none(self):
        from voiceflow.services.dictionary import _build_automaton
        assert _build_automaton([]) is None
        assert _build_automaton([entry("", "X")]) is None
        assert _build_automaton([entry("Y", "")]) is None


# ---------------------------------------------------------------------------
# 2. Snippet substitution tracking
# ---------------------------------------------------------------------------

class TestSnippetSubstitutionTracking:
    def test_exact_match_returns_tuple(self):
        from voiceflow.services.snippets import apply_snippets
        snippets = [snippet("aç parantez", "(")]
        text, subs = apply_snippets("aç parantez", snippets)
        assert text == "("
        assert subs == {"aç parantez": "("}

    def test_case_insensitive_match(self):
        from voiceflow.services.snippets import apply_snippets
        snippets = [snippet("Aç Parantez", "(")]
        text, subs = apply_snippets("aç parantez", snippets)
        assert text == "("
        assert subs is not None

    def test_no_match_returns_none_subs(self):
        from voiceflow.services.snippets import apply_snippets
        snippets = [snippet("aç parantez", "(")]
        text, subs = apply_snippets("farklı bir metin", snippets)
        assert text == "farklı bir metin"
        assert subs is None

    def test_empty_snippets_returns_none_subs(self):
        from voiceflow.services.snippets import apply_snippets
        text, subs = apply_snippets("herhangi metin", [])
        assert text == "herhangi metin"
        assert subs is None

    def test_trailing_punctuation_stripped_before_match(self):
        from voiceflow.services.snippets import apply_snippets
        snippets = [snippet("tamam", "OK")]
        text, subs = apply_snippets("tamam.", snippets)
        assert text == "OK"
        assert subs == {"tamam": "OK"}


# ---------------------------------------------------------------------------
# 3. save_transcription — corrections JSON persistence
# ---------------------------------------------------------------------------

class TestSaveTranscriptionCorrections:
    def test_corrections_serialized_to_json(self):
        """corrections dict must be JSON-serialized before insert."""
        import asyncio
        from voiceflow.db.storage import save_transcription

        corrections = {
            "dict": {"visspar": "Whisper"},
            "snippet": {"aç parantez": "("},
        }

        async def _run():
            with patch("voiceflow.db.storage.aiosqlite.connect") as mock_connect:
                mock_db = AsyncMock()
                mock_cursor = MagicMock()
                mock_cursor.lastrowid = 42
                mock_db.__aenter__ = AsyncMock(return_value=mock_db)
                mock_db.__aexit__ = AsyncMock(return_value=False)
                mock_db.execute = AsyncMock(return_value=mock_cursor)
                mock_db.commit = AsyncMock()
                mock_connect.return_value = mock_db

                row_id = await save_transcription(
                    text="Whisper ile konuştum",
                    raw_text="visspar ile konuştum",
                    corrected=False,
                    corrections=corrections,
                )

                assert row_id == 42
                call_args = mock_db.execute.call_args
                inserted_corrections = call_args[0][1][-1]  # last param in VALUES tuple
                parsed = json.loads(inserted_corrections)
                assert parsed["dict"] == {"visspar": "Whisper"}
                assert parsed["snippet"] == {"aç parantez": "("}

        asyncio.run(_run())

    def test_none_corrections_saves_null(self):
        async def _run():
            from voiceflow.db.storage import save_transcription
            with patch("voiceflow.db.storage.aiosqlite.connect") as mock_connect:
                mock_db = AsyncMock()
                mock_cursor = MagicMock()
                mock_cursor.lastrowid = 1
                mock_db.__aenter__ = AsyncMock(return_value=mock_db)
                mock_db.__aexit__ = AsyncMock(return_value=False)
                mock_db.execute = AsyncMock(return_value=mock_cursor)
                mock_db.commit = AsyncMock()
                mock_connect.return_value = mock_db

                await save_transcription(text="test", corrections=None)

                call_args = mock_db.execute.call_args
                inserted_corrections = call_args[0][1][-1]
                assert inserted_corrections is None

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# 4. RecordingService._apply_text_pipeline — corrections dict built correctly
# ---------------------------------------------------------------------------

class TestPipelineCorrectionsIntegration:
    def _make_service(self, correction_enabled=False):
        from voiceflow.recording.service import RecordingService
        from voiceflow.core.interfaces import TranscriptionResult

        transcriber = MagicMock()
        transcriber.config.model_name = "test-model"

        corrector = MagicMock()
        corrector.config.enabled = correction_enabled
        corrector.config.mode = "general"

        svc = RecordingService(transcriber=transcriber, corrector=corrector)
        return svc, TranscriptionResult

    def test_dict_corrections_in_result(self):
        svc, TranscriptionResult = self._make_service()

        dict_entries = [entry("visspar", "Whisper")]

        async def _run():
            result = TranscriptionResult(text="visspar kullandım", language="tr", duration=1.0)
            with patch("voiceflow.recording.service.get_dictionary", new_callable=AsyncMock, return_value=dict_entries), \
                 patch("voiceflow.recording.service.get_snippets", new_callable=AsyncMock, return_value=[]):
                text, was_corrected, snippet_used, symbol_refs, corrections = await svc._apply_text_pipeline(
                    result, "general", "user-1", None, None, None, asyncio.get_event_loop()
                )
            return text, corrections

        text, corrections = asyncio.run(_run())
        assert "Whisper" in text
        assert "dict" in corrections
        assert corrections["dict"].get("visspar") == "Whisper"

    def test_snippet_corrections_in_result(self):
        svc, TranscriptionResult = self._make_service()

        snippets = [snippet("aç parantez", "(")]

        async def _run():
            result = TranscriptionResult(text="aç parantez", language="tr", duration=1.0)
            with patch("voiceflow.recording.service.get_dictionary", new_callable=AsyncMock, return_value=[]), \
                 patch("voiceflow.recording.service.get_snippets", new_callable=AsyncMock, return_value=snippets):
                text, was_corrected, snippet_used, symbol_refs, corrections = await svc._apply_text_pipeline(
                    result, "general", "user-1", None, None, None, asyncio.get_event_loop()
                )
            return text, snippet_used, corrections

        text, snippet_used, corrections = asyncio.run(_run())
        assert text == "("
        assert snippet_used is True
        assert "snippet" in corrections
        assert corrections["snippet"] == {"aç parantez": "("}

    def test_no_substitutions_empty_corrections(self):
        svc, TranscriptionResult = self._make_service()

        async def _run():
            result = TranscriptionResult(text="normal metin", language="tr", duration=1.0)
            with patch("voiceflow.recording.service.get_dictionary", new_callable=AsyncMock, return_value=[]), \
                 patch("voiceflow.recording.service.get_snippets", new_callable=AsyncMock, return_value=[]):
                _, _, _, _, corrections = await svc._apply_text_pipeline(
                    result, "general", "user-1", None, None, None, asyncio.get_event_loop()
                )
            return corrections

        corrections = asyncio.run(_run())
        assert corrections == {}

    def test_llm_correction_captured_when_text_changes(self):
        svc, TranscriptionResult = self._make_service(correction_enabled=True)
        svc._corrector.config.enabled = True

        async def _run():
            result = TranscriptionResult(text="bugun hava guzel", language="tr", duration=1.0)
            svc._corrector.correct_async = AsyncMock(return_value="Bugün hava güzel.")
            with patch("voiceflow.recording.service.get_dictionary", new_callable=AsyncMock, return_value=[]), \
                 patch("voiceflow.recording.service.get_snippets", new_callable=AsyncMock, return_value=[]):
                text, was_corrected, _, _, corrections = await svc._apply_text_pipeline(
                    result, "general", "user-1", None, None, None, asyncio.get_event_loop()
                )
            return text, was_corrected, corrections

        text, was_corrected, corrections = asyncio.run(_run())
        assert was_corrected is True
        assert "llm" in corrections
        # llm["in"] is text AFTER filler cleaning (pipeline step before LLM)
        assert corrections["llm"]["in"].lower() == "bugun hava guzel"
        assert corrections["llm"]["out"] == "Bugün hava güzel."

    def test_llm_no_change_not_in_corrections(self):
        svc, TranscriptionResult = self._make_service(correction_enabled=True)
        svc._corrector.config.enabled = True

        async def _run():
            result = TranscriptionResult(text="Bugün hava güzel.", language="tr", duration=1.0)
            svc._corrector.correct_async = AsyncMock(return_value="Bugün hava güzel.")
            with patch("voiceflow.recording.service.get_dictionary", new_callable=AsyncMock, return_value=[]), \
                 patch("voiceflow.recording.service.get_snippets", new_callable=AsyncMock, return_value=[]):
                _, was_corrected, _, _, corrections = await svc._apply_text_pipeline(
                    result, "general", "user-1", None, None, None, asyncio.get_event_loop()
                )
            return was_corrected, corrections

        was_corrected, corrections = asyncio.run(_run())
        assert was_corrected is False
        assert "llm" not in corrections

    def test_raw_text_always_saved(self):
        """stop() must always include raw_text in response regardless of correction."""
        from voiceflow.recording.service import RecordingService
        from voiceflow.core.interfaces import TranscriptionResult
        import numpy as np

        transcriber = MagicMock()
        transcriber.config.model_name = "test"
        transcriber.transcribe = MagicMock(
            return_value=TranscriptionResult(text="ham whisper çıktısı", language="tr", duration=1.0)
        )
        corrector = MagicMock()
        corrector.config.enabled = False
        corrector.config.mode = "general"

        svc = RecordingService(transcriber=transcriber, corrector=corrector)
        svc._audio = MagicMock()
        svc._audio.is_recording = True
        svc._audio.stop = MagicMock(return_value=np.zeros(16000, dtype="float32"))

        async def _run():
            with patch("voiceflow.recording.service.save_transcription", new_callable=AsyncMock, return_value=1), \
                 patch("voiceflow.recording.service.get_dictionary", new_callable=AsyncMock, return_value=[]), \
                 patch("voiceflow.recording.service.get_snippets", new_callable=AsyncMock, return_value=[]):
                return await svc.stop(user_id="u1", tenant_id="default")

        result = asyncio.run(_run())
        # raw_text must always be present, not None
        assert result["raw_text"] == "ham whisper çıktısı"
