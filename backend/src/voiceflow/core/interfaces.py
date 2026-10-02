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


class AbstractTranscriber(ABC):
    """Protocol for speech-to-text engines (MLX Whisper, faster-whisper, etc.)"""

    @abstractmethod
    def transcribe(self, audio, sample_rate: int = 16000) -> TranscriptionResult:
        """Transcribe raw audio samples. Returns TranscriptionResult."""

    @abstractmethod
    def preload(self) -> None:
        """Eagerly load the model into memory (called at startup)."""

    @abstractmethod
    def unload(self) -> None:
        """Release model from memory."""


class AbstractCorrector(ABC):
    """Protocol for LLM text correction engines (MLX-LM, Ollama, etc.)"""

    @abstractmethod
    def correct(self, text: str, language: str | None = None, active_app: str | None = None) -> str:
        """Synchronous correction. Used in MLX executor."""

    @abstractmethod
    def preload(self) -> None:
        """Eagerly load / pre-warm the model (called at startup)."""

    @abstractmethod
    def unload(self) -> None:
        """Release model from memory."""


