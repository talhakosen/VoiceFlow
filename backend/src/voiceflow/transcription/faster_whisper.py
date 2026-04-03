"""Server-mode Whisper transcription using faster-whisper (NVIDIA CUDA)."""

import io
import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .whisper import TranscriptionResult, WhisperConfig
from ..core.config import WHISPER_SERVER_MODEL as _FASTER_WHISPER_MODEL

logger = logging.getLogger(__name__)


@dataclass
class FasterWhisperTranscriber:
    """Transcribes audio using faster-whisper on NVIDIA GPU.

    Requires: faster-whisper, soundfile (install with: pip install faster-whisper soundfile)
    Used when BACKEND_MODE=server.
    """

    config: WhisperConfig = field(default_factory=WhisperConfig)
    _model: Any = field(default=None, init=False, repr=False)

    def _ensure_model_loaded(self) -> None:
        """Lazy load faster-whisper model on first use."""
        if self._model is None:
            from faster_whisper import WhisperModel

            model_name = _FASTER_WHISPER_MODEL
            logger.info("Loading faster-whisper %s on CUDA...", model_name)
            self._model = WhisperModel(model_name, device="cuda", compute_type="float16")
            logger.info("faster-whisper model loaded")

    def unload(self) -> None:
        """Release model from GPU memory."""
        import gc

        self._model = None
        gc.collect()
        try:
            import torch
            torch.cuda.empty_cache()
        except ImportError:
            pass  # torch not installed in local dev
        logger.info("faster-whisper model unloaded")

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> TranscriptionResult:
        """Transcribe audio data.

        Args:
            audio: Audio as numpy array (float32, mono, 16kHz)
            sample_rate: Sample rate (default 16000)

        Returns:
            TranscriptionResult with text and detected language
        """
        import soundfile as sf

        self._ensure_model_loaded()

        if len(audio) == 0:
            return TranscriptionResult(text="")

        # faster-whisper requires file-like object, not numpy array
        buf = io.BytesIO()
        sf.write(buf, audio.astype(np.float32), sample_rate, format="WAV")
        buf.seek(0)

        segments, info = self._model.transcribe(
            buf,
            language=self.config.language,  # None = auto-detect
            task=self.config.task,
            vad_filter=True,
            beam_size=5,
        )

        # segments is a generator — consume it fully
        text = " ".join(s.text for s in segments).strip()

        return TranscriptionResult(
            text=text,
            language=info.language,
            duration=len(audio) / sample_rate,
        )
