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
from ..db import get_history, clear_history, get_dictionary, add_dictionary_entry, delete_dictionary_entry

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


# ------------------------------------------------------------------
# Context Engine (Phase 2)
# ------------------------------------------------------------------

class IngestRequest(BaseModel):
    path: str


@router.post("/context/ingest")
async def context_ingest(body: IngestRequest, request: Request):
    """Start background ingestion of a folder into the knowledge base."""
    from ..context.ingestion import ingest_folder
    from ..context.chroma_retriever import ChromaRetriever

    loop = asyncio.get_running_loop()

    async def _run():
        # Reuse or create the retriever so both ingestion and retrieval share the same instance
        svc = request.app.state.recording_service
        retriever = svc.retriever
        if retriever is None:
            retriever = ChromaRetriever()
            svc.update_retriever(retriever)

        result = await loop.run_in_executor(None, ingest_folder, body.path, "default", retriever)
        logger.info(
            "Ingestion done: %d files, %d chunks, %d errors",
            result.files_processed, result.chunks_added, len(result.errors),
        )

    task = asyncio.create_task(_run())
    # Keep a strong reference so GC doesn't collect the task mid-run
    request.app.state.ingest_task = task
    return {"status": "started", "path": body.path, "message": "Indexing in background"}


@router.get("/context/status")
async def context_status(svc=Depends(get_service)):
    """Return knowledge base stats."""
    retriever = svc.retriever
    if retriever is None:
        return {"count": 0, "is_ready": False, "is_empty": True}
    try:
        n = retriever.count()
        return {"count": n, "is_ready": True, "is_empty": n == 0}
    except Exception as e:
        logger.warning("Context status check failed: %s", e)
        return {"count": 0, "is_ready": False, "is_empty": True}


@router.delete("/context")
async def context_clear(svc=Depends(get_service)):
    """Clear the entire knowledge base."""
    retriever = svc.retriever
    if retriever is None:
        return {"status": "nothing_to_clear"}
    try:
        retriever.clear()
        return {"status": "cleared"}
    except Exception as e:
        logger.error("Context clear failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------
# Dictionary (Katman 1)
# ------------------------------------------------------------------

class DictionaryEntryRequest(BaseModel):
    trigger: str
    replacement: str
    scope: str = "personal"


@router.get("/dictionary")
async def get_dict(x_user_id: str | None = Header(default=None, alias="X-User-ID")):
    user_id = x_user_id or ""
    entries = await get_dictionary(user_id=user_id)
    return {"items": entries, "count": len(entries)}


@router.post("/dictionary")
async def add_dict_entry(
    body: DictionaryEntryRequest,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    if not body.trigger.strip() or not body.replacement.strip():
        raise HTTPException(status_code=400, detail="trigger and replacement must not be empty")
    if body.scope not in ("personal", "team"):
        raise HTTPException(status_code=400, detail="scope must be 'personal' or 'team'")
    user_id = x_user_id or ""
    entry_id = await add_dictionary_entry(
        trigger=body.trigger,
        replacement=body.replacement,
        user_id=user_id,
        scope=body.scope,
    )
    return {"id": entry_id, "trigger": body.trigger, "replacement": body.replacement, "scope": body.scope}


@router.delete("/dictionary/{entry_id}")
async def delete_dict_entry(
    entry_id: int,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    user_id = x_user_id or ""
    deleted = await delete_dictionary_entry(entry_id=entry_id, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Entry not found or not yours")
    return {"status": "deleted", "id": entry_id}
