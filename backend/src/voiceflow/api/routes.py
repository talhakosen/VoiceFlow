"""FastAPI routes — HTTP layer only.

Each handler: validate input → call RecordingService → return response.
No business logic here.
"""

import asyncio
import logging
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from .auth import verify_api_key
from ..core.rate_limit import limiter, RATE_LIMIT_STOP
from ..db import save_feedback

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
@limiter.limit(RATE_LIMIT_STOP)
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
    from .parsers import parse_cmd_intervals, parse_it_dataset_index, should_save_pending_wav
    # JWT sets request.state; fall back to X-User-ID header for local mode compat
    state_user_id = getattr(request.state, "user_id", None)
    user_id = state_user_id or x_user_id or None
    tenant_id = getattr(request.state, "tenant_id", "default") or "default"

    cmd_intervals = parse_cmd_intervals(x_cmd_intervals)
    it_dataset_idx = parse_it_dataset_index(x_it_dataset_index)
    save_pending_wav = should_save_pending_wav(x_training_mode, it_dataset_idx)

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
    from ..services.config_service import apply_config
    from ..services.config_service import ConfigRequest as SvcConfigRequest

    tenant_id = getattr(request.state, "tenant_id", "default") or "default"
    user_id = getattr(request.state, "user_id", "") or ""

    svc_config = SvcConfigRequest(
        model=config.model,
        language=config.language,
        task=config.task,
        correction_enabled=config.correction_enabled,
        mode=config.mode,
        output_format=config.output_format,
    )
    result = await apply_config(
        config=svc_config,
        svc=svc,
        app_state=request.app.state,
        backend_mode=_BACKEND_MODE,
        user_id=user_id,
        tenant_id=tenant_id,
    )
    return vars(result)


@router.get("/history")
async def history(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    user_id: str | None = None,
):
    from ..services.history_service import fetch_history
    tenant_id = getattr(request.state, "tenant_id", "default") or "default"
    role = getattr(request.state, "role", "member")
    caller_user_id = getattr(request.state, "user_id", None)
    try:
        return await fetch_history(
            limit=limit,
            offset=offset,
            requested_user_id=user_id,
            caller_user_id=caller_user_id,
            role=role,
            tenant_id=tenant_id,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete("/history")
async def delete_history(request: Request):
    from ..services.history_service import wipe_history
    tenant_id = getattr(request.state, "tenant_id", "default") or "default"
    user_id = getattr(request.state, "user_id", "") or ""
    await wipe_history(tenant_id=tenant_id, user_id=user_id)
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
    from ..services.dictionary_service import list_dictionary
    return await list_dictionary(user_id=x_user_id or "")


@router.post("/dictionary")
async def add_dict_entry(
    body: DictionaryEntryRequest,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    from ..services.dictionary_service import create_dictionary_entry
    try:
        return await create_dictionary_entry(
            trigger=body.trigger,
            replacement=body.replacement,
            user_id=x_user_id or "",
            scope=body.scope,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/dictionary/bundle")
async def load_dict_bundle(x_user_id: str | None = Header(default=None, alias="X-User-ID")):
    """Load the pre-built IT Turkish phonetics bundle into DB (scope=bundle, hidden from UI)."""
    from ..services.dictionary_service import load_dict_bundle as _load
    try:
        return await _load()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/dictionary/bundle")
async def clear_dict_bundle():
    """Remove all bundle entries."""
    from ..services.dictionary_service import wipe_dict_bundle
    return await wipe_dict_bundle()


@router.delete("/dictionary/{entry_id}")
async def delete_dict_entry(
    entry_id: int,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    from ..services.dictionary_service import remove_dictionary_entry
    try:
        await remove_dictionary_entry(entry_id=entry_id, user_id=x_user_id or "")
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
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
    from ..services.dictionary_service import list_snippets
    return await list_snippets(user_id=x_user_id or "")


@router.post("/snippets")
async def add_snippet_route(
    body: SnippetRequest,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    from ..services.dictionary_service import create_snippet
    try:
        return await create_snippet(
            trigger_phrase=body.trigger_phrase,
            expansion=body.expansion,
            user_id=x_user_id or "",
            scope=body.scope,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/snippets/{snippet_id}")
async def delete_snippet_route(
    snippet_id: int,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    from ..services.dictionary_service import remove_snippet
    try:
        await remove_snippet(snippet_id=snippet_id, user_id=x_user_id or "")
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": "deleted", "id": snippet_id}


@router.post("/snippets/pack/{pack_name}")
async def load_snippet_pack_route(
    pack_name: str,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    """Load a pre-built snippet pack (office / engineering). Idempotent."""
    from ..services.dictionary_service import load_snippet_pack
    try:
        return await load_snippet_pack(pack_name=pack_name, user_id=x_user_id or "")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/snippets/pack/{pack_name}")
async def clear_snippet_pack_route(
    pack_name: str,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    """Remove all entries from a snippet pack."""
    from ..services.dictionary_service import clear_snippet_pack
    try:
        return await clear_snippet_pack(pack_name=pack_name, user_id=x_user_id or "")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


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
