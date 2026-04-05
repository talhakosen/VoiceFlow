"""FastAPI routes — HTTP layer only.

Each handler: validate input → call RecordingService → return response.
No business logic here.
"""

import asyncio
import gc
import logging
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from .auth import verify_api_key
from ..db import (
    get_history, clear_history,
    get_dictionary, add_dictionary_entry, delete_dictionary_entry,
    get_snippets, add_snippet, delete_snippet,
    append_audit_log, save_feedback,
)

from ..core.config import BACKEND_MODE as _BACKEND_MODE
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
    processing_ms: int | None = None
    id: int | None = None
    it_wav_path: str | None = None
    pending_wav_path: str | None = None
    symbol_refs: list[str] | None = None


class ConfigRequest(BaseModel):
    model: str | None = None
    language: str | None = None
    task: str | None = None
    correction_enabled: bool | None = None
    mode: Literal["general", "engineering", "office"] | None = None
    output_format: Literal["prose", "code_comment", "pr_description", "jira_ticket"] | None = None


# ------------------------------------------------------------------
# Dependency: RecordingService from app.state
# ------------------------------------------------------------------

def get_service(request: Request):
    return request.app.state.recording_service


# ------------------------------------------------------------------
# Recording endpoints
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
    x_cmd_intervals: str | None = Header(default=None, alias="X-Cmd-Intervals"),
    x_it_dataset_index: str | None = Header(default=None, alias="X-IT-Dataset-Index"),
    x_training_mode: str | None = Header(default=None, alias="X-Training-Mode"),
):
    # JWT sets request.state; fall back to X-User-ID header for local mode compat
    state_user_id = getattr(request.state, "user_id", None)
    user_id = state_user_id or x_user_id or None
    tenant_id = getattr(request.state, "tenant_id", "default") or "default"

    # Parse "1.10-2.30,4.50-5.10" → [(1.10, 2.30), (4.50, 5.10)]
    cmd_intervals: list[tuple[float, float]] | None = None
    if x_cmd_intervals:
        try:
            cmd_intervals = [
                (float(a), float(b))
                for part in x_cmd_intervals.split(",")
                for a, b in [part.strip().split("-", 1)]
            ]
        except Exception:
            cmd_intervals = None

    it_dataset_idx: int | None = None
    if x_it_dataset_index:
        try:
            it_dataset_idx = int(x_it_dataset_index)
        except ValueError:
            it_dataset_idx = None

    save_pending_wav = x_training_mode == "1" and it_dataset_idx is None

    try:
        result = await svc.stop(
            user_id=user_id,
            tenant_id=tenant_id,
            active_app=x_active_app or None,
            window_title=x_window_title or None,
            selected_text=x_selected_text or None,
            cmd_intervals=cmd_intervals,
            it_dataset_index=it_dataset_idx,
            save_pending_wav=save_pending_wav,
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

    # Update mode — engineering mode auto-disables LLM correction
    if config.mode is not None:
        corrector.config.mode = config.mode
        if config.mode == "engineering" and corrector.config.enabled:
            logger.info("Engineering mode: auto-disabling LLM correction")
            corrector.config.enabled = False
            from ..recording import _mlx_executor
            if hasattr(corrector, "correct_async"):
                await loop.run_in_executor(None, corrector.unload)
            else:
                await loop.run_in_executor(_mlx_executor, corrector.unload)

        if config.mode == "engineering":
            import time as _time
            last_paths = getattr(request.app.state, "last_index_paths", {})
            req_user_id = getattr(request.state, "user_id", "") or ""
            entry = last_paths.get(req_user_id) or last_paths.get("default")
            if entry and (_time.time() - entry["indexed_at"]) > 300:
                async def _reindex(path: str, uid: str, app_state) -> None:
                    try:
                        from ..symbol import build_symbol_index, generate_project_notes
                        sym_count = await build_symbol_index(path, uid)
                        logger.info("Auto re-index (engineering mode): %d symbols", sym_count)
                        if sym_count > 0:
                            await generate_project_notes(path, uid)
                        import time as _t
                        if not hasattr(app_state, "last_index_paths"):
                            app_state.last_index_paths = {}
                        app_state.last_index_paths[uid] = {"path": path, "indexed_at": _t.time()}
                    except Exception as _e:
                        logger.warning("Auto re-index failed: %s", _e)
                asyncio.create_task(_reindex(entry["path"], req_user_id, request.app.state))

    # Update output format
    if config.output_format is not None:
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
    role = getattr(request.state, "role", "member")
    caller_user_id = getattr(request.state, "user_id", None)

    # Tenant isolation: only admin/superadmin can query other users' history
    if user_id is not None and user_id != caller_user_id:
        if role not in ("admin", "superadmin"):
            raise HTTPException(status_code=403, detail="Cannot access other users' history")

    # Non-admin without explicit user_id: scope to self
    if user_id is None and role not in ("admin", "superadmin") and caller_user_id:
        user_id = caller_user_id

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


@router.post("/dictionary/bundle")
async def load_dict_bundle(x_user_id: str | None = Header(default=None, alias="X-User-ID")):
    """Load the pre-built IT Turkish phonetics bundle into DB (scope=bundle, hidden from UI)."""
    import json as _json
    from pathlib import Path
    from ..db.storage import load_bundle_entries
    bundle_path = Path(__file__).parents[4] / "ml" / "dictionary" / "it_bundle_full.json"
    if not bundle_path.exists():
        raise HTTPException(status_code=404, detail="Bundle file not found")
    with open(bundle_path, encoding="utf-8") as f:
        entries = _json.load(f)
    count = await load_bundle_entries(tenant_id="default", entries=entries)
    return {"status": "loaded", "count": count}


@router.delete("/dictionary/bundle")
async def clear_dict_bundle():
    """Remove all bundle entries."""
    from ..db.storage import clear_bundle_entries
    await clear_bundle_entries(tenant_id="default")
    return {"status": "cleared"}


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
# Feedback (training signal)
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
