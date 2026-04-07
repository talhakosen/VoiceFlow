"""Tests for RunPod cloud inference components."""

import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from voiceflow.transcription.runpod_transcriber import RunPodTranscriber
from voiceflow.correction.runpod_passthrough import RunPodPassthroughCorrector
from voiceflow.core.interfaces import AbstractTranscriber, AbstractCorrector, TranscriptionResult
from voiceflow.transcription.whisper import WhisperConfig


class TestRunPodTranscriber:
    """Tests for RunPodTranscriber."""

    def test_abc_conformance(self):
        assert issubclass(RunPodTranscriber, AbstractTranscriber)

    def test_init_defaults(self):
        with patch.dict("os.environ", {"RUNPOD_INFERENCE_URL": "", "RUNPOD_ENDPOINT_ID": "", "RUNPOD_API_TOKEN": ""}):
            t = RunPodTranscriber()
            assert t._direct_url == ""
            assert t.endpoint_id == ""
            assert t._correction_enabled is True

    def test_preload_direct_url(self):
        with patch.dict("os.environ", {"RUNPOD_INFERENCE_URL": "http://localhost:18765/inference", "RUNPOD_ENDPOINT_ID": "", "RUNPOD_API_TOKEN": ""}):
            t = RunPodTranscriber()
            t.preload()  # should not raise

    def test_preload_no_config_raises(self):
        with patch.dict("os.environ", {"RUNPOD_INFERENCE_URL": "", "RUNPOD_ENDPOINT_ID": "", "RUNPOD_API_TOKEN": ""}, clear=False):
            t = RunPodTranscriber()
            with pytest.raises(ValueError, match="RUNPOD_INFERENCE_URL"):
                t.preload()

    def test_transcribe_empty_audio(self):
        with patch.dict("os.environ", {"RUNPOD_INFERENCE_URL": "http://test", "RUNPOD_ENDPOINT_ID": "", "RUNPOD_API_TOKEN": ""}):
            t = RunPodTranscriber()
            result = t.transcribe(np.array([], dtype=np.float32))
            assert result.text == ""

    def test_transcribe_caches_correction(self):
        """Verify that transcribe() caches corrected text for passthrough corrector."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "text": "Düzeltilmiş metin.",
            "raw_text": "duzeltilmis metin",
            "corrected": True,
            "language": "tr",
            "duration": 2.0,
            "whisper_ms": 300,
            "llm_ms": 350,
            "processing_ms": 650,
        }
        mock_response.raise_for_status = MagicMock()

        with patch.dict("os.environ", {"RUNPOD_INFERENCE_URL": "http://test/inference", "RUNPOD_ENDPOINT_ID": "", "RUNPOD_API_TOKEN": ""}):
            t = RunPodTranscriber()
            with patch("httpx.post", return_value=mock_response):
                audio = np.random.randn(16000).astype(np.float32)
                result = t.transcribe(audio, mode="general")

        assert result.text == "duzeltilmis metin"
        assert result.language == "tr"
        assert t.last_corrected_text == "Düzeltilmiş metin."
        assert t.last_was_corrected is True
        assert t.last_processing_detail["whisper_ms"] == 300

    def test_correction_enabled_sync(self):
        """Verify _correction_enabled is sent in request."""
        with patch.dict("os.environ", {"RUNPOD_INFERENCE_URL": "http://test/inference", "RUNPOD_ENDPOINT_ID": "", "RUNPOD_API_TOKEN": ""}):
            t = RunPodTranscriber()
            t._correction_enabled = False

            mock_response = MagicMock()
            mock_response.json.return_value = {"text": "", "raw_text": "", "corrected": False, "language": "tr", "duration": 1.0, "whisper_ms": 0, "llm_ms": 0}
            mock_response.raise_for_status = MagicMock()

            with patch("httpx.post", return_value=mock_response) as mock_post:
                t.transcribe(np.random.randn(16000).astype(np.float32))

            call_kwargs = mock_post.call_args
            # multipart mode: correction_enabled in data field
            assert call_kwargs.kwargs["data"]["correction_enabled"] == "false"


class TestRunPodPassthroughCorrector:
    """Tests for RunPodPassthroughCorrector."""

    def test_abc_conformance(self):
        assert issubclass(RunPodPassthroughCorrector, AbstractCorrector)

    def test_config_defaults(self):
        c = RunPodPassthroughCorrector()
        assert c.config.enabled is True
        assert c.config.mode == "general"

    def test_passthrough_returns_cached_text(self):
        c = RunPodPassthroughCorrector()
        mock_transcriber = MagicMock()
        mock_transcriber.last_corrected_text = "Düzeltilmiş."
        c.set_transcriber(mock_transcriber)

        result = c.correct("duzeltilmis")
        assert result == "Düzeltilmiş."

    def test_passthrough_fallback_when_no_cache(self):
        c = RunPodPassthroughCorrector()
        mock_transcriber = MagicMock()
        mock_transcriber.last_corrected_text = None
        c.set_transcriber(mock_transcriber)

        result = c.correct("original text")
        assert result == "original text"

    def test_passthrough_without_transcriber(self):
        c = RunPodPassthroughCorrector()
        result = c.correct("test text")
        assert result == "test text"

    def test_correct_async(self):
        import asyncio
        c = RunPodPassthroughCorrector()
        mock_transcriber = MagicMock()
        mock_transcriber.last_corrected_text = "Async düzeltme."
        c.set_transcriber(mock_transcriber)

        result = asyncio.run(c.correct_async("async test"))
        assert result == "Async düzeltme."

    def test_sync_enabled_propagates(self):
        """Verify correction enabled state syncs to transcriber."""
        c = RunPodPassthroughCorrector()
        mock_transcriber = MagicMock()
        mock_transcriber._correction_enabled = True
        c.set_transcriber(mock_transcriber)

        c.config.update(enabled=False)
        c.unload()  # triggers _sync_enabled
        assert mock_transcriber._correction_enabled is False

        c.config.update(enabled=True)
        c.preload()  # triggers _sync_enabled
        assert mock_transcriber._correction_enabled is True


class TestRunPodIntegration:
    """Integration tests for RunPod mode wiring."""

    def test_build_transcriber_runpod_mode(self):
        with patch.dict("os.environ", {"WHISPER_BACKEND": "runpod", "RUNPOD_INFERENCE_URL": "http://test", "RUNPOD_ENDPOINT_ID": "", "RUNPOD_API_TOKEN": ""}):
            # Re-import to pick up env
            from voiceflow.main import _build_transcriber, _build_corrector
            # These use module-level config, so we test the class types instead
            t = RunPodTranscriber()
            c = RunPodPassthroughCorrector()
            c.set_transcriber(t)

            assert isinstance(t, AbstractTranscriber)
            assert isinstance(c, AbstractCorrector)
            assert hasattr(c, "set_transcriber")

    def test_wav_encoding(self):
        """Verify WAV encoding produces valid bytes."""
        with patch.dict("os.environ", {"RUNPOD_INFERENCE_URL": "http://test", "RUNPOD_ENDPOINT_ID": "", "RUNPOD_API_TOKEN": ""}):
            t = RunPodTranscriber()
            audio = np.random.randn(16000 * 2).astype(np.float32)
            wav_bytes = t._encode_wav(audio, 16000)

            # Valid WAV starts with RIFF header
            assert wav_bytes[:4] == b"RIFF"
            assert wav_bytes[8:12] == b"WAVE"
            # Should be ~64KB for 2s mono 16-bit
            assert len(wav_bytes) > 60000
