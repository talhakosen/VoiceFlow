"""Whisper transcription module using mlx-whisper."""

import logging
from dataclasses import dataclass, field
from ..core.config import (
    WHISPER_MODEL as _WHISPER_MODEL,
    WHISPER_IT_MODEL as _WHISPER_IT_MODEL,
    WHISPER_DYNAMIC_WINDOW as _WHISPER_DYNAMIC_WINDOW,
)
from .dynamic_window import compute_window, encoder_window, has_repeated_span, FULL_WINDOW_S
from typing import Any

import mlx.core as mx
import numpy as np

logger = logging.getLogger(__name__)


# Bilinen Whisper fixed-phrase hallüsinasyonları (YouTube training data kalıntıları)
_HALLUCINATION_PHRASES = [
    "izlediğiniz için teşekkür ederim",
    "izlediğiniz için teşekkürler",
    "abone olmayı unutmayın",
    "beğenmeyi unutmayın",
    "altyazı m.k.",
    "altyazı:",
    "thank you for watching",
    "thanks for watching",
    "please subscribe",
    "don't forget to subscribe",
    "subtitles by",
]


def _strip_hallucination_phrases(text: str) -> str:
    """Bilinen sabit hallüsinasyon cümlelerini metnin sonundan sil.
    casefold() kullanılır — lower() Türkçe İ→i dönüşümünü yapmaz.
    """
    folded = text.casefold().rstrip(" .")
    for phrase in _HALLUCINATION_PHRASES:
        if folded.endswith(phrase.casefold()):
            stripped = text[:len(folded) - len(phrase)].rstrip(" .,")
            logger.warning("Hallucination phrase stripped: %r", phrase)
            return stripped
    return text


def _strip_hallucination_loop(text: str, max_repeats: int = 3) -> str:
    """Whisper tekrar loop'unu temizle: 'Yar Yar Yar Yar...' → ''

    Ardışık aynı kelime veya n-gram max_repeats kez tekrarlanıyorsa,
    ilk tekrar başladığı noktadan itibaren metnin geri kalanını sil.
    """
    words = text.split()
    if len(words) < max_repeats * 2:
        return text

    for n in range(1, 4):  # unigram, bigram, trigram
        for i in range(len(words) - n * max_repeats + 1):
            gram = tuple(words[i:i + n])
            repeats = 0
            j = i + n
            while j + n <= len(words) + 1 and tuple(words[j:j + n]) == gram:
                repeats += 1
                j += n
            if repeats >= max_repeats:
                stripped = " ".join(words[:i]).strip()
                logger.warning("Hallucination loop detected (%dx %r) — stripped tail", repeats + 1, " ".join(gram))
                return stripped

    return text


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

    model_name: str = field(default_factory=lambda: _WHISPER_MODEL)
    language: str | None = "tr"  # Default Turkish, None for auto-detect
    task: str = "transcribe"  # "transcribe" = same language, "translate" = to English
    it_model_name: str | None = field(default_factory=lambda: _WHISPER_IT_MODEL or None)
    dynamic_window: bool = field(default_factory=lambda: _WHISPER_DYNAMIC_WINDOW)


@dataclass
class WhisperTranscriber:
    """Transcribes audio using mlx-whisper."""

    config: WhisperConfig = field(default_factory=WhisperConfig)
    _model_loaded: bool = field(default=False, init=False)

    def preload(self) -> None:
        """Load weights AND compile Metal kernels via a tiny dummy transcription.

        mlx-whisper loads lazily on first `transcribe()`, so without this the
        *first* real dictation pays ~9s for model load + kernel compilation.
        Warming here moves that cost to startup (background).
        """
        if not self._model_loaded:
            self.warm()
            self._model_loaded = True

    def warm(self) -> None:
        """Run a tiny dummy transcription to (re)compile Metal kernels and page
        in weights. Idempotent and cheap (~1-4s).

        Call at startup AND again after a heavy Metal event — loading the ~5GB
        LLM re-cools whisper's compiled state, so the first real dictation after
        enabling correction would otherwise pay the full cold cost again.
        """
        import time

        import mlx_whisper

        t0 = time.perf_counter()
        try:
            # 1s of quiet tone — enough to run encoder+decoder and compile.
            warm = (0.01 * np.sin(2 * np.pi * 220 * np.arange(16000) / 16000)).astype(np.float32)
            options = {
                "path_or_hf_repo": self.config.model_name,
                "task": self.config.task,
                "temperature": 0.0,
                "condition_on_previous_text": False,
            }
            if self.config.language:
                options["language"] = self.config.language
            mlx_whisper.transcribe(warm, **options)
            mx.metal.clear_cache()
            logger.info("Whisper warmed in %.0fms", (time.perf_counter() - t0) * 1000)
        except Exception as e:  # best-effort; never block
            logger.warning("Whisper warm-up failed: %s", e)

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

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000, mode: str | None = None) -> TranscriptionResult:
        """Transcribe audio data.

        Args:
            audio: Audio data as numpy array (float32, mono)
            sample_rate: Sample rate of audio (default 16000)
            mode: Active mode ("general" | "engineering"). Engineering mode
                  uses the IT-specific fine-tuned model when configured.

        Returns:
            TranscriptionResult with text and metadata
        """
        import mlx_whisper

        self.preload()

        if len(audio) == 0:
            return TranscriptionResult(text="")

        # Ensure audio is float32
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        # Normalize audio if needed
        if np.abs(audio).max() > 1.0:
            audio = audio / np.abs(audio).max()

        # Select model: use IT-specific model for engineering mode when available
        model_path = self.config.model_name
        if mode == "engineering" and self.config.it_model_name:
            model_path = self.config.it_model_name
            logger.debug("Engineering mode: using IT model %s", model_path)

        # Build transcription options
        options = {
            "path_or_hf_repo": model_path,
            "task": self.config.task,
            "temperature": 0.0,               # greedy decoding — beam_size=1 equivalent, ~2x hız
            "condition_on_previous_text": False,  # her segment bağımsız, daha hızlı
        }

        if self.config.language:
            options["language"] = self.config.language

        duration = len(audio) / sample_rate
        window = compute_window(duration) if self.config.dynamic_window else FULL_WINDOW_S

        if window < FULL_WINDOW_S:
            # Timestamp token'ları 30sn pencereye göre eğitilmiş; kısa pencerede
            # seek döngüsü kilitlenebiliyor. Dikte akışında segment zamanı kullanılmıyor.
            options["without_timestamps"] = True

        result = self._run(mlx_whisper, audio, options, model_path, window)
        raw_text = result.get("text", "").strip()

        # Kısa pencere nadiren tüm cümleyi tekrarlatıyor. Yakalarsak tam
        # pencereyle bir kez daha dene — yavaş ama doğru.
        if window < FULL_WINDOW_S and has_repeated_span(raw_text):
            logger.warning(
                "Repetition at %ds window (%.1fs audio) — retrying at %ds",
                window, duration, FULL_WINDOW_S,
            )
            options.pop("without_timestamps", None)
            result = self._run(mlx_whisper, audio, options, model_path, FULL_WINDOW_S)
            raw_text = result.get("text", "").strip()

        text = _strip_hallucination_phrases(_strip_hallucination_loop(raw_text))
        return TranscriptionResult(
            text=text,
            language=result.get("language"),
            duration=duration,
        )

    def _run(self, mlx_whisper, audio, options: dict, model_path: str, window: int) -> dict:
        """Tek transkripsiyon çağrısı — verilen encoder penceresiyle."""
        import time

        t0 = time.perf_counter()
        with encoder_window(model_path, window):
            result = mlx_whisper.transcribe(audio, **options)
        mx.metal.clear_cache()  # Metal buffer'ları serbest bırak, bellek şişmesin
        logger.info(
            "Whisper %.1fs audio @ %ds window → %.0fms",
            len(audio) / 16000, window, (time.perf_counter() - t0) * 1000,
        )
        return result

    def transcribe_file(self, file_path: str) -> TranscriptionResult:
        """Transcribe audio file.

        Args:
            file_path: Path to audio file

        Returns:
            TranscriptionResult with text and metadata
        """
        import mlx_whisper

        self.preload()

        options = {
            "path_or_hf_repo": self.config.model_name,
            "task": self.config.task,
            "temperature": 0.0,
            "condition_on_previous_text": False,
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
