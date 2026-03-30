"""FastAPI routes — HTTP layer only.

Each handler: validate input → call RecordingService → return response.
No business logic here.
"""

import asyncio
import gc
import logging
import os

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from .auth import verify_api_key
from ..db import get_history, clear_history

_BACKEND_MODE = os.getenv("BACKEND_MODE", "local")
logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(verify_api_key)])


# ------------------------------------------------------------------
# Schemas
# ------------------------------------------------------------------

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
    task: str | None = None          # "transcribe" | "translate"
    correction_enabled: bool | None = None
    mode: str | None = None          # "general" | "engineering" | "office"


# ------------------------------------------------------------------
# Dependency: RecordingService from app.state
# ------------------------------------------------------------------

def get_service(request: Request):
    return request.app.state.recording_service


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@router.get("/status", response_model=StatusResponse)
async def get_status(svc=Depends(get_service)):
    return StatusResponse(status=svc.state, is_recording=svc.is_recording)


@router.post("/start", response_model=StatusResponse)
async def start_recording(svc=Depends(get_service)):
    try:
        svc.start()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return StatusResponse(status=svc.state, is_recording=svc.is_recording)


@router.post("/stop", response_model=TranscriptionResponse)
async def stop_recording(
    request: Request,
    svc=Depends(get_service),
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    try:
        result = await svc.stop(user_id=x_user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return TranscriptionResponse(**result)


@router.post("/force-stop")
async def force_stop(svc=Depends(get_service)):
    was_recording = svc.force_stop()
    return {"status": "stopped", "was_recording": was_recording}


@router.get("/devices")
async def get_devices(svc=Depends(get_service)):
    return {"devices": svc.get_devices()}


@router.post("/config")
async def update_config(config: ConfigRequest, svc=Depends(get_service)):
    from ..transcription import WhisperTranscriber, WhisperConfig
    from concurrent.futures import ThreadPoolExecutor

    loop = asyncio.get_running_loop()
    mlx_executor = svc._mlx_executor if hasattr(svc, "_mlx_executor") else None

    transcriber = svc.transcriber
    corrector = svc.corrector

    # Update transcriber if config changed
    new_cfg = WhisperConfig(
        model_name=config.model or transcriber.config.model_name,
        language=config.language if config.language is not None else transcriber.config.language,
        task=config.task or transcriber.config.task,
    )
    if (new_cfg.model_name != transcriber.config.model_name
            or new_cfg.language != transcriber.config.language
            or new_cfg.task != transcriber.config.task):
        transcriber.unload()
        if _BACKEND_MODE == "server":
            from ..transcription.faster_whisper import FasterWhisperTranscriber
            svc.update_transcriber(FasterWhisperTranscriber(config=new_cfg))
        else:
            svc.update_transcriber(WhisperTranscriber(config=new_cfg))
        gc.collect()

    # Update mode
    if config.mode is not None:
        corrector.config.mode = config.mode

    # Update correction enabled/disabled
    if config.correction_enabled is not None:
        was_enabled = corrector.config.enabled
        corrector.config.enabled = config.correction_enabled

        from ..services.recording import _mlx_executor
        if config.correction_enabled and not was_enabled:
            logger.info("Correction enabled, loading LLM model...")
            if hasattr(corrector, "correct_async"):
                await loop.run_in_executor(None, corrector._ensure_model_loaded)
            else:
                await loop.run_in_executor(_mlx_executor, corrector._ensure_model_loaded)
        elif not config.correction_enabled and was_enabled:
            logger.info("Correction disabled, unloading LLM model...")
            if hasattr(corrector, "correct_async"):
                await loop.run_in_executor(None, corrector.unload)
            else:
                await loop.run_in_executor(_mlx_executor, corrector.unload)

    return {
        "model": svc.transcriber.config.model_name,
        "language": svc.transcriber.config.language,
        "task": svc.transcriber.config.task,
        "correction_enabled": corrector.config.enabled,
        "mode": corrector.config.mode,
    }


@router.get("/history")
async def history(limit: int = 100, offset: int = 0, user_id: str | None = None):
    rows = await get_history(limit=limit, offset=offset, user_id=user_id)
    return {"items": rows, "count": len(rows)}


@router.delete("/history")
async def delete_history():
    await clear_history()
    return {"status": "cleared"}
