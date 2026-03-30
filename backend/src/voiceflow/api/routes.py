"""FastAPI routes for WhisperFlow."""

import asyncio
import gc
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from .auth import verify_api_key
from ..db import save_transcription, get_history, clear_history

_BACKEND_MODE = os.getenv("BACKEND_MODE", "local")

logger = logging.getLogger(__name__)

from ..audio import AudioCapture, AudioConfig
from ..audio.capture import RecordingState
from ..correction import LLMCorrector, CorrectorConfig
from ..transcription import WhisperTranscriber, WhisperConfig

router = APIRouter(dependencies=[Depends(verify_api_key)])

# Global instances
_audio_capture: AudioCapture | None = None
_transcriber: Any = None   # WhisperTranscriber | FasterWhisperTranscriber
_corrector: Any = None     # LLMCorrector | OllamaCorrector

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
    id: int | None = None


class ConfigRequest(BaseModel):
    model: str | None = None
    language: str | None = None
    task: str | None = None  # "transcribe" or "translate"
    correction_enabled: bool | None = None
    mode: str | None = None  # "general" | "engineering" | "office"


def get_audio_capture() -> AudioCapture:
    global _audio_capture
    if _audio_capture is None:
        _audio_capture = AudioCapture(config=AudioConfig())
    return _audio_capture


def get_transcriber():
    global _transcriber
    if _transcriber is None:
        if _BACKEND_MODE == "server":
            from ..transcription.faster_whisper import FasterWhisperTranscriber
            _transcriber = FasterWhisperTranscriber(config=WhisperConfig())
        else:
            _transcriber = WhisperTranscriber(config=WhisperConfig())
    return _transcriber


def get_corrector():
    global _corrector
    if _corrector is None:
        if _BACKEND_MODE == "server":
            from ..correction.ollama_corrector import OllamaCorrector, OllamaCorrectorConfig
            _corrector = OllamaCorrector(config=OllamaCorrectorConfig())
        else:
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
async def stop_recording(x_user_id: str | None = Header(default=None, alias="X-User-ID")):
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
    loop = asyncio.get_running_loop()
    t_whisper = time.perf_counter()
    result = await loop.run_in_executor(_mlx_executor, transcriber.transcribe, audio_data)
    t_whisper_done = time.perf_counter()
    logger.info("Whisper transcription: %.3fs → '%s'", t_whisper_done - t_whisper, result.text[:80])

    # Apply LLM correction if enabled
    raw_text = result.text
    was_corrected = False
    corrector = get_corrector()
    active_mode = corrector.config.mode  # capture before any concurrent /config change
    if corrector.config.enabled and result.text:
        logger.info("LLM correction enabled, correcting: '%s'", result.text[:80])
        t_llm = time.perf_counter()
        # Ollama uses async HTTP — run directly; MLX uses GPU executor
        if hasattr(corrector, "correct_async"):
            corrected_text = await corrector.correct_async(result.text, result.language)
        else:
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

    row_id = await save_transcription(
        text=result.text,
        raw_text=raw_text if was_corrected else None,
        corrected=was_corrected,
        language=result.language,
        duration=result.duration,
        mode=active_mode,
        user_id=x_user_id,
    )

    return TranscriptionResponse(
        text=result.text,
        raw_text=raw_text if was_corrected else None,
        corrected=was_corrected,
        language=result.language,
        duration=result.duration,
        id=row_id,
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
        language=config.language if config.language is not None else current.config.language,
        task=config.task or current.config.task,
    )

    # Only recreate transcriber if config actually changed
    if (new_config.model_name != current.config.model_name
            or new_config.language != current.config.language
            or new_config.task != current.config.task):
        current.unload()
        if _BACKEND_MODE == "server":
            from ..transcription.faster_whisper import FasterWhisperTranscriber
            _transcriber = FasterWhisperTranscriber(config=new_config)
        else:
            _transcriber = WhisperTranscriber(config=new_config)
        gc.collect()

    # Update correction config if provided
    corrector = get_corrector()
    if config.correction_enabled is not None:
        was_enabled = corrector.config.enabled
        corrector.config.enabled = config.correction_enabled

        loop = asyncio.get_running_loop()
        # Load model on demand when correction is enabled
        if config.correction_enabled and not was_enabled:
            logger.info("Correction enabled, loading LLM model...")
            if hasattr(corrector, "correct_async"):
                await loop.run_in_executor(None, corrector._ensure_model_loaded)
            else:
                await loop.run_in_executor(_mlx_executor, corrector._ensure_model_loaded)
        # Unload model when correction is disabled
        elif not config.correction_enabled and was_enabled:
            logger.info("Correction disabled, unloading LLM model...")
            if hasattr(corrector, "correct_async"):
                await loop.run_in_executor(None, corrector.unload)
            else:
                await loop.run_in_executor(_mlx_executor, corrector.unload)

    if config.mode is not None:
        corrector.config.mode = config.mode

    transcriber = get_transcriber()
    return {
        "model": transcriber.config.model_name,
        "language": transcriber.config.language,
        "task": transcriber.config.task,
        "correction_enabled": corrector.config.enabled,
        "mode": corrector.config.mode,
    }


@router.get("/history")
async def history(limit: int = 100, offset: int = 0, user_id: str | None = None):
    """Return transcription history from SQLite, newest first. Filter by user_id if provided."""
    rows = await get_history(limit=limit, offset=offset, user_id=user_id)
    return {"items": rows, "count": len(rows)}


@router.delete("/history")
async def delete_history():
    """Clear all transcription history."""
    await clear_history()
    return {"status": "cleared"}
