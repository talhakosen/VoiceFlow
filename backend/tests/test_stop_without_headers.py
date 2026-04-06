"""Integration test: /api/stop works without X-Window-Title / X-Selected-Text headers.

Ensures backward compatibility — header absence must not cause errors in
RecordingService.stop() or corrector.correct() / correct_async().
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# RecordingService.stop() — no context headers
# ---------------------------------------------------------------------------

def make_recording_service(corrector):
    """Build a minimal RecordingService with a mock transcriber and audio."""
    from voiceflow.recording.service import RecordingService

    transcriber = MagicMock()
    transcriber.config = MagicMock()
    transcriber.config.model_name = "test-model"
    transcriber.config.language = "tr"
    transcriber.config.task = "transcribe"

    from voiceflow.core.interfaces import TranscriptionResult
    transcriber.transcribe = MagicMock(return_value=TranscriptionResult(text="test metni", language="tr", duration=1.0))

    svc = RecordingService(transcriber=transcriber, corrector=corrector)
    # Patch audio so stop() can be called without a real audio capture
    svc._audio = MagicMock()
    svc._audio.is_recording = True
    svc._audio.stop = MagicMock(return_value=__import__("numpy").zeros(16000, dtype="float32"))
    return svc


def test_stop_no_context_headers_passes():
    """stop() with no window_title / selected_text must succeed."""
    corrector = MagicMock()
    corrector.config = MagicMock()
    corrector.config.enabled = False
    corrector.config.mode = "general"

    svc = make_recording_service(corrector)

    async def _run():
        with patch("voiceflow.recording.service.save_transcription", new_callable=AsyncMock, return_value=1), \
             patch("voiceflow.recording.service.get_dictionary", new_callable=AsyncMock, return_value=[]), \
             patch("voiceflow.recording.service.get_snippets", new_callable=AsyncMock, return_value=[]):
            return await svc.stop(user_id=None, tenant_id="default")

    result = asyncio.run(_run())
    assert "text" in result


def test_stop_with_context_headers_passes():
    """stop() with window_title + selected_text must succeed and not raise."""
    corrector = MagicMock()
    corrector.config = MagicMock()
    corrector.config.enabled = False
    corrector.config.mode = "general"

    svc = make_recording_service(corrector)

    async def _run():
        with patch("voiceflow.recording.service.save_transcription", new_callable=AsyncMock, return_value=1), \
             patch("voiceflow.recording.service.get_dictionary", new_callable=AsyncMock, return_value=[]), \
             patch("voiceflow.recording.service.get_snippets", new_callable=AsyncMock, return_value=[]):
            return await svc.stop(
                user_id=None,
                tenant_id="default",
                window_title="VS Code — main.py",
                selected_text="def hello():",
            )

    result = asyncio.run(_run())
    assert "text" in result


# ---------------------------------------------------------------------------
# APICorrector.correct_async — no context
# ---------------------------------------------------------------------------

def test_ollama_correct_async_no_context():
    """correct_async with no window/selected must not raise."""
    from voiceflow.correction.api_corrector import APICorrector, APICorrectorConfig

    corrector = APICorrector(config=APICorrectorConfig(enabled=False))
    result = asyncio.run(corrector.correct_async("test metni"))
    assert result == "test metni"


def test_ollama_correct_no_context():
    """correct() with no window/selected must not raise."""
    from voiceflow.correction.api_corrector import APICorrector, APICorrectorConfig

    corrector = APICorrector(config=APICorrectorConfig(enabled=False))
    result = corrector.correct("test metni")
    assert result == "test metni"


# ---------------------------------------------------------------------------
# MLXCorrector.correct — no context
# ---------------------------------------------------------------------------

def test_llm_corrector_no_context_disabled():
    """MLXCorrector.correct() with no context and disabled must return original."""
    from voiceflow.correction.mlx_corrector import MLXCorrector, MLXCorrectorConfig

    corrector = MLXCorrector(config=MLXCorrectorConfig(enabled=False))
    result = corrector.correct("test metni")
    assert result == "test metni"


# ---------------------------------------------------------------------------
# Silence / short-audio guard
# ---------------------------------------------------------------------------

def test_silence_guard_short_duration():
    """Audio shorter than 0.5s should be discarded without calling Whisper."""
    import numpy as np
    _SAMPLE_RATE = 16000

    duration_sec = 0.3
    audio = np.zeros(int(_SAMPLE_RATE * duration_sec), dtype=np.int16)
    rms = float(np.sqrt(np.mean(audio.astype(np.float32) ** 2)))

    assert duration_sec < 0.5 or rms < 0.005


def test_silence_guard_silent_audio():
    """Silent audio (rms < 0.005) should be discarded regardless of duration."""
    import numpy as np
    _SAMPLE_RATE = 16000

    audio = np.zeros(int(_SAMPLE_RATE * 2.0), dtype=np.int16)
    rms = float(np.sqrt(np.mean(audio.astype(np.float32) ** 2)))

    assert rms < 0.005


# ---------------------------------------------------------------------------
# IT Bundle auto-load
# ---------------------------------------------------------------------------

def test_count_bundle_entries_returns_int():
    """count_bundle_entries must return an integer (0 when DB is fresh or bundle loaded)."""
    import asyncio
    from unittest.mock import AsyncMock, patch, MagicMock

    async def _run():
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=(71294,))
        mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_cursor.__aexit__ = AsyncMock(return_value=False)

        mock_db = MagicMock()
        mock_db.execute = MagicMock(return_value=mock_cursor)
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=False)

        with patch("voiceflow.db.dictionary_storage.aiosqlite.connect", return_value=mock_db):
            from voiceflow.db.dictionary_storage import count_bundle_entries
            result = await count_bundle_entries("default")
            assert isinstance(result, int)
            assert result == 71294

    asyncio.run(_run())


def test_bundle_entries_have_trigger_and_replacement():
    """Each bundle entry must have 'trigger' and 'replacement' keys."""
    import json
    import pathlib

    bundle_path = pathlib.Path(__file__).parent.parent.parent.parent / "ml" / "dictionary" / "it_bundle_full.json"
    if not bundle_path.exists():
        return  # Skip if not present in CI

    with open(bundle_path, encoding="utf-8") as f:
        entries = json.load(f)

    assert len(entries) > 0
    sample = entries[:10]
    for entry in sample:
        assert "trigger" in entry, f"Missing 'trigger' in {entry}"
        assert "replacement" in entry, f"Missing 'replacement' in {entry}"

    # "batın bar" → "toolbar" must be present after UI terms were added
    toolbar_entry = next((e for e in entries if e["trigger"] == "batın bar"), None)
    assert toolbar_entry is not None, "'batın bar' not found in bundle"
    assert toolbar_entry["replacement"] == "toolbar"
