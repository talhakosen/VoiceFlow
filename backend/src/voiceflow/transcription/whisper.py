"""Whisper transcription module using mlx-whisper."""

from dataclasses import dataclass, field
from typing import Any

import numpy as np


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

    model_name: str = "mlx-community/whisper-small-mlx"
    language: str | None = "tr"  # Turkish default, None for auto-detect
    task: str = "transcribe"  # or "translate"


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

        return TranscriptionResult(
            text=result.get("text", "").strip(),
            language=result.get("language"),
            segments=result.get("segments"),
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

        return TranscriptionResult(
            text=result.get("text", "").strip(),
            language=result.get("language"),
            segments=result.get("segments"),
        )
