"""RecordingService — orchestrates audio capture, transcription, and correction.

Single responsibility: coordinate the start→stop→transcribe→correct→persist pipeline.
Routes delegate to this service; they only handle HTTP concerns.
"""

import asyncio
import functools
import logging
import time
from concurrent.futures import ThreadPoolExecutor

from ..audio import AudioCapture, AudioConfig
from ..core.interfaces import AbstractCorrector, AbstractTranscriber, TranscriptionResult
from ..db import save_transcription, get_dictionary, get_snippets
from ..services.dictionary import apply_dictionary
from ..services.snippets import apply_snippets

logger = logging.getLogger(__name__)

# Single-thread executor for MLX operations (Metal GPU is not thread-safe)
_mlx_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mlx")


_SAMPLE_RATE = 16000
_MIN_CHUNK_SECONDS = 0.3  # daha kısa parçaları atla (gürültü)


async def _transcribe_segmented(
    audio_data,
    cmd_intervals: list[tuple[float, float]],
    transcriber: "AbstractTranscriber",
    user_id: str,
    loop,
) -> tuple[str, str | None, float]:
    """Sesi cmd aralıklarına göre böl, her parçayı ayrı transcribe et.

    Cmd-held parçalar → transcribe → inject_symbol_refs
    Normal parçalar   → transcribe → olduğu gibi bırak

    word_timestamps kullanılmaz — Whisper'a ekstra yük yok.

    Returns: (merged_text, language, total_duration_seconds)
    """
    import numpy as np
    from .symbol_indexer import inject_symbol_refs

    total_samples = len(audio_data)
    total_duration = total_samples / _SAMPLE_RATE

    # Tüm segmentleri (start, end, is_cmd) olarak listele
    segments: list[tuple[float, float, bool]] = []
    prev = 0.0
    for s, e in sorted(cmd_intervals):
        s = max(0.0, min(s, total_duration))
        e = max(0.0, min(e, total_duration))
        if s > prev + _MIN_CHUNK_SECONDS:
            segments.append((prev, s, False))
        if e > s + _MIN_CHUNK_SECONDS:
            segments.append((s, e, True))
        prev = e
    if prev + _MIN_CHUNK_SECONDS < total_duration:
        segments.append((prev, total_duration, False))

    parts: list[str] = []
    detected_language: str | None = None

    for start, end, is_cmd in segments:
        chunk = audio_data[int(start * _SAMPLE_RATE): int(end * _SAMPLE_RATE)]
        if len(chunk) < int(_MIN_CHUNK_SECONDS * _SAMPLE_RATE):
            continue
        seg_result = await loop.run_in_executor(_mlx_executor, transcriber.transcribe, chunk)
        if not seg_result.text.strip():
            continue
        if detected_language is None and seg_result.language:
            detected_language = seg_result.language
        text = seg_result.text.strip()
        if is_cmd and user_id:
            text = await inject_symbol_refs(text, user_id)
            logger.info("Cmd segment injected: '%s'", text[:80])
        parts.append(text)

    return " ".join(parts), detected_language, total_duration


class RecordingService:
    """Coordinates the full voice recording pipeline.

    Injected with concrete transcriber and corrector implementations —
    swap out for mocks in tests or for different backend modes.
    """

    def __init__(
        self,
        transcriber: AbstractTranscriber,
        corrector: AbstractCorrector,
    ) -> None:
        self._audio = AudioCapture(config=AudioConfig())
        self._transcriber = transcriber
        self._corrector = corrector

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    @property
    def is_recording(self) -> bool:
        return self._audio.is_recording

    @property
    def state(self) -> str:
        return self._audio.state.value

    def get_devices(self) -> list:
        return self._audio.get_devices()

    # ------------------------------------------------------------------
    # Recording lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start audio capture. Raises ValueError if already recording."""
        if self._audio.is_recording:
            raise ValueError("Already recording")
        self._audio.start()

    async def stop(
        self,
        user_id: str | None = None,
        tenant_id: str = "default",
        active_app: str | None = None,
        window_title: str | None = None,
        selected_text: str | None = None,
        cmd_intervals: list[tuple[float, float]] | None = None,
    ) -> dict:
        """Stop recording, transcribe, optionally correct, persist to DB.

        Returns a dict ready for the API response.
        """
        if not self._audio.is_recording:
            raise ValueError("Not recording")

        t_start = time.perf_counter()
        audio_data = self._audio.stop()
        logger.info("Audio capture stop: %.3fs, samples: %d", time.perf_counter() - t_start, len(audio_data))

        if len(audio_data) == 0:
            return {"text": "", "duration": 0.0}

        loop = asyncio.get_running_loop()

        t_whisper = time.perf_counter()
        if cmd_intervals:
            # Sesi böl: cmd parçaları ayrı transcribe → inject, diğerleri düz
            merged_text, language, duration = await _transcribe_segmented(
                audio_data, cmd_intervals, self._transcriber, user_id, loop
            )
            result = TranscriptionResult(text=merged_text, language=language, duration=duration)
        else:
            result = await loop.run_in_executor(_mlx_executor, self._transcriber.transcribe, audio_data)
        logger.info("Whisper: %.3fs → '%s'", time.perf_counter() - t_whisper, result.text[:80])

        raw_text = result.text
        was_corrected = False
        snippet_used = False
        active_mode = self._corrector.config.mode  # capture before concurrent /config can mutate

        # Dictionary substitution (Whisper → Dictionary → Snippets → LLM)
        if result.text and user_id:
            entries = await get_dictionary(user_id=user_id, include_smart=True)
            if entries:
                result.text = apply_dictionary(result.text, entries)
            snippets = await get_snippets(user_id=user_id)
            if snippets:
                expanded = apply_snippets(result.text, snippets)
                if expanded != result.text:
                    snippet_used = True
                result.text = expanded

        # Correct (if enabled)
        if self._corrector.config.enabled and result.text:
            t_llm = time.perf_counter()
            if hasattr(self._corrector, "correct_async"):
                corrected = await self._corrector.correct_async(
                    result.text, result.language, None, active_app,
                    window_title=window_title, selected_text=selected_text,
                )
            else:
                _correct_fn = functools.partial(
                    self._corrector.correct,
                    result.text, result.language, None, active_app,
                    window_title=window_title, selected_text=selected_text,
                )
                corrected = await loop.run_in_executor(_mlx_executor, _correct_fn)
            logger.info("LLM correction: %.3fs", time.perf_counter() - t_llm)
            if corrected != result.text:
                was_corrected = True
                logger.info("Corrected: '%s' → '%s'", result.text[:60], corrected[:60])
            result.text = corrected

        processing_ms = int((time.perf_counter() - t_start) * 1000)
        logger.info("Total stop→result: %dms", processing_ms)

        # Persist
        row_id = await save_transcription(
            text=result.text,
            raw_text=raw_text if was_corrected else None,
            corrected=was_corrected,
            language=result.language,
            duration=result.duration,
            mode=active_mode,
            user_id=user_id,
            tenant_id=tenant_id,
            processing_ms=processing_ms,
        )

        logger.info("snippet_used=%s user_id=%s", snippet_used, user_id)
        return {
            "text": result.text,
            "raw_text": raw_text if was_corrected else None,
            "corrected": was_corrected,
            "snippet_used": snippet_used,
            "language": result.language,
            "duration": result.duration,
            "processing_ms": processing_ms,
            "id": row_id,
        }

    def force_stop(self) -> bool:
        """Force-stop regardless of state. Returns True if was recording."""
        was_recording = self._audio.is_recording
        if was_recording:
            self._audio.stop()
        else:
            self._audio.force_reset()
        return was_recording

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    def update_transcriber(self, new_transcriber: AbstractTranscriber) -> None:
        self._transcriber = new_transcriber

    def update_corrector(self, new_corrector: AbstractCorrector) -> None:
        self._corrector = new_corrector

    @property
    def transcriber(self) -> AbstractTranscriber:
        return self._transcriber

    @property
    def corrector(self) -> AbstractCorrector:
        return self._corrector

    # ------------------------------------------------------------------
    # Model preload (called at startup)
    # ------------------------------------------------------------------

    async def preload_models(self) -> None:
        loop = asyncio.get_running_loop()
        logger.info("Preloading Whisper model...")
        try:
            await loop.run_in_executor(_mlx_executor, self._transcriber._ensure_model_loaded)
            logger.info("Whisper model loaded")
        except Exception as e:
            logger.error("Whisper model load failed: %s", e)

        if self._corrector.config.enabled:
            logger.info("Preloading LLM model...")
            try:
                if hasattr(self._corrector, "correct_async"):
                    await loop.run_in_executor(None, self._corrector._ensure_model_loaded)
                else:
                    await loop.run_in_executor(_mlx_executor, self._corrector._ensure_model_loaded)
                logger.info("LLM model loaded")
            except Exception as e:
                logger.error("LLM model load failed: %s", e)
        else:
            logger.info("LLM correction disabled, skipping preload")
