"""Abstract interfaces for VoiceFlow components.

Depend on these abstractions, not on concrete implementations.
This enables loose coupling and testability (inject mocks in tests).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class TranscriptionResult:
    """Domain model for a transcription result."""
    text: str
    language: str | None = None
    duration: float | None = None


@dataclass
class CorrectorConfig:
    """Shared corrector configuration."""
    enabled: bool = False
    mode: str = "general"  # "general" | "engineering" | "office"


class AbstractTranscriber(ABC):
    """Protocol for speech-to-text engines (MLX Whisper, faster-whisper, etc.)"""

    @abstractmethod
    def transcribe(self, audio, sample_rate: int = 16000) -> TranscriptionResult:
        """Transcribe raw audio samples. Returns TranscriptionResult."""

    @abstractmethod
    def _ensure_model_loaded(self) -> None:
        """Eagerly load the model (called during preload)."""

    @abstractmethod
    def unload(self) -> None:
        """Release model from memory."""


class AbstractCorrector(ABC):
    """Protocol for LLM text correction engines (MLX-LM, Ollama, etc.)"""

    config: CorrectorConfig

    @abstractmethod
    def correct(self, text: str, language: str | None = None) -> str:
        """Synchronous correction. Used in MLX executor."""

    @abstractmethod
    def _ensure_model_loaded(self) -> None:
        """Eagerly load / pre-warm the model."""

    @abstractmethod
    def unload(self) -> None:
        """Release model from memory."""
