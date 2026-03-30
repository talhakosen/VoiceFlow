"""FastAPI routes for WhisperFlow."""

import asyncio
import gc
import logging
import time
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

from ..audio import AudioCapture, AudioConfig
from ..audio.capture import RecordingState
from ..correction import LLMCorrector, CorrectorConfig
from ..transcription import WhisperTranscriber, WhisperConfig

router = APIRouter()

# Global instances
_audio_capture: AudioCapture | None = None
_transcriber: WhisperTranscriber | None = None
_corrector: LLMCorrector | None = None

# Single-thread executor for MLX operations (Metal GPU is not thread-safe)
_mlx_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mlx")


class StatusResponse(BaseModel):
    status: str
    is_recording: bool


class TranscriptionResponse(BaseModel):
    text: str
    raw_text: str | None = None
    corrected: bool = False
    language: str | None = None
    duration: float | None = None


class ConfigRequest(BaseModel):
    model: str | None = None
    language: str | None = None
    task: str | None = None  # "transcribe" or "translate"
    correction_enabled: bool | None = None


def get_audio_capture() -> AudioCapture:
    global _audio_capture
    if _audio_capture is None:
        _audio_capture = AudioCapture(config=AudioConfig())
    return _audio_capture


def get_transcriber() -> WhisperTranscriber:
    global _transcriber
    if _transcriber is None:
        _transcriber = WhisperTranscriber(config=WhisperConfig())
    return _transcriber


def get_corrector() -> LLMCorrector:
    global _corrector
    if _corrector is None:
        _corrector = LLMCorrector(config=CorrectorConfig())
    return _corrector


@router.get("/status", response_model=StatusResponse)
async def get_status():
    """Get current recording status."""
    capture = get_audio_capture()
    return StatusResponse(
        status=capture.state.value,
        is_recording=capture.is_recording,
    )


@router.post("/start", response_model=StatusResponse)
async def start_recording():
    """Start recording audio."""
    capture = get_audio_capture()
    if capture.is_recording:
        raise HTTPException(status_code=400, detail="Already recording")
    capture.start()
    return StatusResponse(
        status=capture.state.value,
        is_recording=capture.is_recording,
    )


@router.post("/stop", response_model=TranscriptionResponse)
async def stop_recording():
    """Stop recording and transcribe."""
    capture = get_audio_capture()
    if not capture.is_recording:
        raise HTTPException(status_code=400, detail="Not recording")

    # Stop and get audio
    t_start = time.perf_counter()
    audio_data = capture.stop()
    t_stop = time.perf_counter()
    logger.info("Audio capture stop: %.3fs, samples: %d", t_stop - t_start, len(audio_data))

    if len(audio_data) == 0:
        return TranscriptionResponse(text="", duration=0)

    # Transcribe in dedicated MLX thread (Metal GPU is not thread-safe)
    transcriber = get_transcriber()
    loop = asyncio.get_event_loop()
    t_whisper = time.perf_counter()
    result = await loop.run_in_executor(_mlx_executor, transcriber.transcribe, audio_data)
    t_whisper_done = time.perf_counter()
    logger.info("Whisper transcription: %.3fs → '%s'", t_whisper_done - t_whisper, result.text[:80])

    # Apply LLM correction if enabled
    raw_text = result.text
    was_corrected = False
    corrector = get_corrector()
    if corrector.config.enabled and result.text:
        logger.info("LLM correction enabled, correcting: '%s'", result.text[:80])
        t_llm = time.perf_counter()
        corrected_text = await loop.run_in_executor(
            _mlx_executor, corrector.correct, result.text, result.language
        )
        t_llm_done = time.perf_counter()
        logger.info("LLM correction: %.3fs", t_llm_done - t_llm)
        if corrected_text != result.text:
            was_corrected = True
            logger.info("LLM corrected: '%s' → '%s'", result.text[:80], corrected_text[:80])
        else:
            logger.info("LLM correction: no changes needed")
        result.text = corrected_text

    t_total = time.perf_counter()
    logger.info("Total stop→response: %.3fs", t_total - t_start)

    return TranscriptionResponse(
        text=result.text,
        raw_text=raw_text if was_corrected else None,
        corrected=was_corrected,
        language=result.language,
        duration=result.duration,
    )


@router.post("/force-stop")
async def force_stop():
    """Force stop recording regardless of state. Always succeeds."""
    capture = get_audio_capture()
    was_recording = capture.is_recording
    if was_recording:
        capture.stop()
        logger.info("Force stop: was recording, stopped")
    else:
        # Ensure stream is closed even if state is inconsistent
        if capture._stream is not None:
            try:
                capture._stream.stop()
                capture._stream.close()
                capture._stream = None
                logger.warning("Force stop: stream was open despite not recording state")
            except Exception as e:
                logger.error("Force stop: error closing stream: %s", e)
        capture._state = RecordingState.IDLE
        logger.info("Force stop: was not recording")

    return {"status": "stopped", "was_recording": was_recording}


@router.get("/devices")
async def get_devices():
    """Get available audio input devices."""
    capture = get_audio_capture()
    return {"devices": capture.get_devices()}


@router.post("/config")
async def update_config(config: ConfigRequest):
    """Update transcription configuration."""
    global _transcriber

    current = get_transcriber()
    new_config = WhisperConfig(
        model_name=config.model or current.config.model_name,
        language=config.language,  # None = auto-detect
        task=config.task or current.config.task,
    )

    # Only recreate transcriber if config actually changed
    if (new_config.model_name != current.config.model_name
            or new_config.language != current.config.language
            or new_config.task != current.config.task):
        current.unload()
        _transcriber = WhisperTranscriber(config=new_config)
        gc.collect()

    # Update correction config if provided
    corrector = get_corrector()
    if config.correction_enabled is not None:
        was_enabled = corrector.config.enabled
        corrector.config.enabled = config.correction_enabled

        loop = asyncio.get_event_loop()
        # Load model on demand when correction is enabled
        if config.correction_enabled and not was_enabled:
            logger.info("Correction enabled, loading LLM model...")
            await loop.run_in_executor(_mlx_executor, corrector._ensure_model_loaded)
        # Unload model when correction is disabled
        elif not config.correction_enabled and was_enabled:
            logger.info("Correction disabled, unloading LLM model...")
            await loop.run_in_executor(_mlx_executor, corrector.unload)

    transcriber = get_transcriber()
    return {
        "model": transcriber.config.model_name,
        "language": transcriber.config.language,
        "task": transcriber.config.task,
        "correction_enabled": corrector.config.enabled,
    }
