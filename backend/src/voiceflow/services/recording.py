"""RecordingService — orchestrates audio capture, transcription, and correction.

Single responsibility: coordinate the start→stop→transcribe→correct→persist pipeline.
Routes delegate to this service; they only handle HTTP concerns.
"""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor

from ..audio import AudioCapture, AudioConfig
from ..audio.capture import RecordingState
from ..core.interfaces import AbstractCorrector, AbstractTranscriber, TranscriptionResult
from ..db import save_transcription

logger = logging.getLogger(__name__)

# Single-thread executor for MLX operations (Metal GPU is not thread-safe)
_mlx_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mlx")


class RecordingService:
    """Coordinates the full voice recording pipeline.

    Injected with concrete transcriber and corrector implementations —
    swap out for mocks in tests or for different backend modes.
    """

    def __init__(self, transcriber: AbstractTranscriber, corrector: AbstractCorrector) -> None:
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

    async def stop(self, user_id: str | None = None) -> dict:
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

        # Transcribe
        t_whisper = time.perf_counter()
        result: TranscriptionResult = await loop.run_in_executor(
            _mlx_executor, self._transcriber.transcribe, audio_data
        )
        logger.info("Whisper: %.3fs → '%s'", time.perf_counter() - t_whisper, result.text[:80])

        raw_text = result.text
        was_corrected = False
        active_mode = self._corrector.config.mode  # capture before concurrent /config can mutate

        # Correct (if enabled)
        if self._corrector.config.enabled and result.text:
            t_llm = time.perf_counter()
            if hasattr(self._corrector, "correct_async"):
                corrected = await self._corrector.correct_async(result.text, result.language)
            else:
                corrected = await loop.run_in_executor(
                    _mlx_executor, self._corrector.correct, result.text, result.language
                )
            logger.info("LLM correction: %.3fs", time.perf_counter() - t_llm)
            if corrected != result.text:
                was_corrected = True
                logger.info("Corrected: '%s' → '%s'", result.text[:60], corrected[:60])
            result.text = corrected

        logger.info("Total stop→result: %.3fs", time.perf_counter() - t_start)

        # Persist
        row_id = await save_transcription(
            text=result.text,
            raw_text=raw_text if was_corrected else None,
            corrected=was_corrected,
            language=result.language,
            duration=result.duration,
            mode=active_mode,
            user_id=user_id,
        )

        return {
            "text": result.text,
            "raw_text": raw_text if was_corrected else None,
            "corrected": was_corrected,
            "language": result.language,
            "duration": result.duration,
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
