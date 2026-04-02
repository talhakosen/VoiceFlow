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
from ..db import (
    get_history, clear_history,
    get_dictionary, add_dictionary_entry, delete_dictionary_entry,
    get_snippets, add_snippet, delete_snippet,
    append_audit_log, save_feedback,
)

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
    snippet_used: bool = False
    language: str | None = None
    duration: float | None = None
    id: int | None = None


class ConfigRequest(BaseModel):
    model: str | None = None
    language: str | None = None
    task: str | None = None          # "transcribe" | "translate"
    correction_enabled: bool | None = None
    mode: str | None = None          # "general" | "engineering" | "office"
    output_format: str | None = None  # "prose" | "code_comment" | "pr_description" | "jira_ticket"


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
    x_active_app: str | None = Header(default=None, alias="X-Active-App"),
    x_window_title: str | None = Header(default=None, alias="X-Window-Title"),
    x_selected_text: str | None = Header(default=None, alias="X-Selected-Text"),
):
    # JWT sets request.state; fall back to X-User-ID header for local mode compat
    state_user_id = getattr(request.state, "user_id", None)
    user_id = state_user_id or x_user_id or None
    tenant_id = getattr(request.state, "tenant_id", "default") or "default"
    try:
        result = await svc.stop(
            user_id=user_id,
            tenant_id=tenant_id,
            active_app=x_active_app or None,
            window_title=x_window_title or None,
            selected_text=x_selected_text or None,
        )
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
async def update_config(config: ConfigRequest, request: Request, svc=Depends(get_service)):
    from ..transcription import WhisperTranscriber, WhisperConfig

    loop = asyncio.get_running_loop()

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

    # Update output format
    if config.output_format is not None:
        valid_formats = {"prose", "code_comment", "pr_description", "jira_ticket"}
        if config.output_format not in valid_formats:
            raise HTTPException(status_code=400, detail=f"output_format must be one of {sorted(valid_formats)}")
        corrector.config.output_format = config.output_format

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

    result = {
        "model": svc.transcriber.config.model_name,
        "language": svc.transcriber.config.language,
        "task": svc.transcriber.config.task,
        "correction_enabled": corrector.config.enabled,
        "mode": corrector.config.mode,
        "output_format": getattr(corrector.config, "output_format", "prose"),
    }
    tenant_id = getattr(request.state, "tenant_id", "default") or "default"
    user_id = getattr(request.state, "user_id", "") or ""
    await append_audit_log(
        tenant_id=tenant_id,
        action="config_changed",
        user_id=user_id,
        target=str({k: v for k, v in config.model_dump().items() if v is not None}),
    )
    return result


@router.get("/history")
async def history(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    user_id: str | None = None,
):
    tenant_id = getattr(request.state, "tenant_id", "default") or "default"
    rows = await get_history(limit=limit, offset=offset, user_id=user_id, tenant_id=tenant_id)
    return {"items": rows, "count": len(rows)}


@router.delete("/history")
async def delete_history(request: Request):
    tenant_id = getattr(request.state, "tenant_id", "default") or "default"
    user_id = getattr(request.state, "user_id", "") or ""
    await clear_history()
    await append_audit_log(tenant_id=tenant_id, action="history_cleared", user_id=user_id)
    return {"status": "cleared"}


# ------------------------------------------------------------------
# Context Engine (Phase 2)
# ------------------------------------------------------------------

class IngestRequest(BaseModel):
    path: str


@router.post("/context/ingest")
async def context_ingest(
    body: IngestRequest,
    request: Request,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    """Scan folder, extract identifiers, populate smart dictionary."""
    from ..services.smart_dictionary import build_smart_dictionary

    user_id = x_user_id or getattr(request.state, "user_id", None) or "default"

    async def _run():
        try:
            added = await build_smart_dictionary(body.path, user_id)
            logger.info("Smart dictionary: %d entries added for user %s", added, user_id)
        except Exception as e:
            logger.warning("Smart dictionary failed: %s", e)
        try:
            from ..services.symbol_indexer import build_symbol_index
            sym_count = await build_symbol_index(body.path, user_id)
            logger.info("Symbol index: %d symbols for user %s", sym_count, user_id)
        except Exception as e:
            logger.warning("Symbol index failed: %s", e)

    task = asyncio.create_task(_run())
    request.app.state.ingest_task = task
    return {"status": "started", "path": body.path, "message": "Smart dictionary scan in background"}


@router.get("/context/status")
async def context_status(
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    request: Request = None,
):
    """Return smart dictionary entry count."""
    import aiosqlite
    from pathlib import Path
    user_id = x_user_id or getattr(request.state, "user_id", None) or "default"
    db_path = Path.home() / ".voiceflow" / "voiceflow.db"
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM user_dictionary WHERE user_id = ? AND scope = 'smart'",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            n = row[0] if row else 0
    return {"count": n, "is_ready": True, "is_empty": n == 0}


@router.get("/context/projects")
async def context_projects(
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    request: Request = None,
):
    """Return indexed projects with smart dictionary + symbol counts."""
    import aiosqlite
    from pathlib import Path
    user_id = x_user_id or getattr(request.state, "user_id", None) or "default"
    db_path = Path.home() / ".voiceflow" / "voiceflow.db"
    async with aiosqlite.connect(db_path) as db:
        # Symbol counts per project
        async with db.execute(
            "SELECT project_path, COUNT(*) FROM symbol_index WHERE user_id = ? GROUP BY project_path",
            (user_id,),
        ) as cursor:
            symbol_rows = {row[0]: row[1] for row in await cursor.fetchall()}

        # Smart dictionary total (all belong to latest ingest — no per-project tracking yet)
        async with db.execute(
            "SELECT COUNT(*) FROM user_dictionary WHERE user_id = ? AND scope = 'smart'",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            smart_total = row[0] if row else 0

    projects = []
    for path, sym_count in symbol_rows.items():
        projects.append({
            "path": path,
            "name": Path(path).name,
            "symbol_count": sym_count,
        })

    return {
        "projects": projects,
        "smart_word_count": smart_total,
        "total_symbols": sum(p["symbol_count"] for p in projects),
    }


@router.get("/symbol/lookup")
async def symbol_lookup(
    q: str,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    request: Request = None,
    limit: int = 5,
):
    """Fuzzy symbol lookup. Returns file_path:line_number matches."""
    from ..services.symbol_indexer import lookup_symbol
    user_id = x_user_id or getattr(request.state, "user_id", None) or "default"
    results = await lookup_symbol(query=q, user_id=user_id, limit=limit)
    return {"query": q, "results": results}


@router.delete("/context")
async def context_clear(
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    request: Request = None,
):
    """Clear smart dictionary entries for this user."""
    import aiosqlite
    from pathlib import Path
    user_id = x_user_id or getattr(request.state, "user_id", None) or "default"
    db_path = Path.home() / ".voiceflow" / "voiceflow.db"
    async with aiosqlite.connect(db_path) as db:
        await db.execute("DELETE FROM user_dictionary WHERE user_id = ?", (user_id,))
        await db.commit()
    return {"status": "cleared"}


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


# ------------------------------------------------------------------
# Snippets (Katman 1)
# ------------------------------------------------------------------

class SnippetRequest(BaseModel):
    trigger_phrase: str
    expansion: str
    scope: str = "personal"


@router.get("/snippets")
async def get_snippets_route(x_user_id: str | None = Header(default=None, alias="X-User-ID")):
    user_id = x_user_id or ""
    items = await get_snippets(user_id=user_id)
    return {"items": items, "count": len(items)}


@router.post("/snippets")
async def add_snippet_route(
    body: SnippetRequest,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    if not body.trigger_phrase.strip() or not body.expansion.strip():
        raise HTTPException(status_code=400, detail="trigger_phrase and expansion must not be empty")
    if body.scope not in ("personal", "team"):
        raise HTTPException(status_code=400, detail="scope must be 'personal' or 'team'")
    user_id = x_user_id or ""
    snippet_id = await add_snippet(
        trigger_phrase=body.trigger_phrase,
        expansion=body.expansion,
        user_id=user_id,
        scope=body.scope,
    )
    return {"id": snippet_id, "trigger_phrase": body.trigger_phrase, "expansion": body.expansion, "scope": body.scope}


@router.delete("/snippets/{snippet_id}")
async def delete_snippet_route(
    snippet_id: int,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    user_id = x_user_id or ""
    deleted = await delete_snippet(snippet_id=snippet_id, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Snippet not found or not yours")
    return {"status": "deleted", "id": snippet_id}


# ------------------------------------------------------------------
# Training Mode — Feedback (Katman 4)
# ------------------------------------------------------------------

_VALID_ACTIONS = {"approved", "edited", "dismissed"}


class FeedbackRequest(BaseModel):
    raw_whisper: str
    model_output: str
    user_action: str   # 'approved' | 'edited' | 'dismissed'
    user_edit: str | None = None
    app_context: str | None = None
    window_title: str | None = None
    mode: str | None = None
    language: str | None = None


@router.post("/feedback")
async def submit_feedback(req: FeedbackRequest, request: Request):
    if req.user_action not in _VALID_ACTIONS:
        raise HTTPException(status_code=400, detail=f"user_action must be one of {sorted(_VALID_ACTIONS)}")
    user_id = getattr(request.state, "user_id", None)
    tenant_id = getattr(request.state, "tenant_id", "default") or "default"
    await save_feedback(
        raw_whisper=req.raw_whisper,
        model_output=req.model_output,
        user_action=req.user_action,
        tenant_id=tenant_id,
        user_id=user_id,
        user_edit=req.user_edit,
        app_context=req.app_context,
        window_title=req.window_title,
        mode=req.mode,
        language=req.language,
    )
    return {"status": "ok"}
