"""Whisper transcription module using mlx-whisper."""

import logging
import os
from dataclasses import dataclass, field
from typing import Any

import mlx.core as mx
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    """Result of transcription."""

    text: str
    language: str | None = None
    segments: list[dict] | None = None
    duration: float | None = None


@dataclass
class WhisperConfig:
    """Whisper model configuration."""

    model_name: str = os.getenv("WHISPER_MODEL", "mlx-community/whisper-large-v3-turbo")
    language: str | None = "tr"  # Default Turkish, None for auto-detect
    task: str = "transcribe"  # "transcribe" = same language, "translate" = to English


@dataclass
class WhisperTranscriber:
    """Transcribes audio using mlx-whisper."""

    config: WhisperConfig = field(default_factory=WhisperConfig)
    _model_loaded: bool = field(default=False, init=False)

    def _ensure_model_loaded(self) -> None:
        """Lazy load model on first use."""
        if not self._model_loaded:
            # mlx-whisper downloads model on first use
            import mlx_whisper
            self._model_loaded = True

    def unload(self) -> None:
        """Unload model from memory by clearing mlx-whisper's internal cache."""
        import gc
        import mlx_whisper
        # mlx_whisper caches models internally; clear what we can
        if hasattr(mlx_whisper, '_cache'):
            mlx_whisper._cache.clear()
        self._model_loaded = False
        gc.collect()
        mx.metal.clear_cache()
        logger.info("Whisper model cache cleared")

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> TranscriptionResult:
        """Transcribe audio data.

        Args:
            audio: Audio data as numpy array (float32, mono)
            sample_rate: Sample rate of audio (default 16000)

        Returns:
            TranscriptionResult with text and metadata
        """
        import mlx_whisper

        self._ensure_model_loaded()

        if len(audio) == 0:
            return TranscriptionResult(text="")

        # Ensure audio is float32
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        # Normalize audio if needed
        if np.abs(audio).max() > 1.0:
            audio = audio / np.abs(audio).max()

        # Build transcription options
        options = {
            "path_or_hf_repo": self.config.model_name,
            "task": self.config.task,
        }

        if self.config.language:
            options["language"] = self.config.language

        # Transcribe
        result = mlx_whisper.transcribe(audio, **options)

        # Free Metal GPU buffers to prevent memory growth
        mx.metal.clear_cache()

        return TranscriptionResult(
            text=result.get("text", "").strip(),
            language=result.get("language"),
            duration=len(audio) / sample_rate,
        )

    def transcribe_file(self, file_path: str) -> TranscriptionResult:
        """Transcribe audio file.

        Args:
            file_path: Path to audio file

        Returns:
            TranscriptionResult with text and metadata
        """
        import mlx_whisper

        self._ensure_model_loaded()

        options = {
            "path_or_hf_repo": self.config.model_name,
            "task": self.config.task,
        }

        if self.config.language:
            options["language"] = self.config.language

        result = mlx_whisper.transcribe(file_path, **options)

        # Free Metal GPU buffers to prevent memory growth
        mx.metal.clear_cache()

        return TranscriptionResult(
            text=result.get("text", "").strip(),
            language=result.get("language"),
        )
