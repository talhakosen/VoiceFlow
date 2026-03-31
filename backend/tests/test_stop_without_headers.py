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
    from voiceflow.services.recording import RecordingService

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
        with patch("voiceflow.services.recording.save_transcription", new_callable=AsyncMock, return_value=1), \
             patch("voiceflow.services.recording.get_dictionary", new_callable=AsyncMock, return_value=[]), \
             patch("voiceflow.services.recording.get_snippets", new_callable=AsyncMock, return_value=[]):
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
        with patch("voiceflow.services.recording.save_transcription", new_callable=AsyncMock, return_value=1), \
             patch("voiceflow.services.recording.get_dictionary", new_callable=AsyncMock, return_value=[]), \
             patch("voiceflow.services.recording.get_snippets", new_callable=AsyncMock, return_value=[]):
            return await svc.stop(
                user_id=None,
                tenant_id="default",
                window_title="VS Code — main.py",
                selected_text="def hello():",
            )

    result = asyncio.run(_run())
    assert "text" in result


# ---------------------------------------------------------------------------
# OllamaCorrector.correct_async — no context
# ---------------------------------------------------------------------------

def test_ollama_correct_async_no_context():
    """correct_async with no window/selected must not raise."""
    from voiceflow.correction.ollama_corrector import OllamaCorrector, OllamaCorrectorConfig

    corrector = OllamaCorrector(config=OllamaCorrectorConfig(enabled=False))
    result = asyncio.run(corrector.correct_async("test metni"))
    assert result == "test metni"


def test_ollama_correct_no_context():
    """correct() with no window/selected must not raise."""
    from voiceflow.correction.ollama_corrector import OllamaCorrector, OllamaCorrectorConfig

    corrector = OllamaCorrector(config=OllamaCorrectorConfig(enabled=False))
    result = corrector.correct("test metni")
    assert result == "test metni"


# ---------------------------------------------------------------------------
# LLMCorrector.correct — no context
# ---------------------------------------------------------------------------

def test_llm_corrector_no_context_disabled():
    """LLMCorrector.correct() with no context and disabled must return original."""
    from voiceflow.correction.llm_corrector import LLMCorrector, CorrectorConfig

    corrector = LLMCorrector(config=CorrectorConfig(enabled=False))
    result = corrector.correct("test metni")
    assert result == "test metni"
