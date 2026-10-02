"""FastAPI routes — HTTP layer only.

Each handler: validate input → call RecordingService → return response.
No business logic here.
"""

import asyncio
import dataclasses
import logging
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel

from .auth import verify_api_key
from ..core.rate_limit import limiter, RATE_LIMIT_STOP
from ..services.auth_service import require_role
from ..services.feedback_service import record_feedback as _record_feedback

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
    language: str | None = None
    duration: float | None = None
    processing_ms: int | None = None
    id: int | None = None
    pending_wav_path: str | None = None
    notice: str | None = None  # kullanıcıya gösterilecek uyarı (ör. mikrofon izni yok)


class ConfigRequest(BaseModel):
    model: str | None = None
    language: str | None = None
    task: str | None = None
    correction_enabled: bool | None = None
    mode: Literal["general", "engineering"] | None = None
    output_format: Literal["prose", "code_comment", "pr_description", "jira_ticket"] | None = None
    input_device: str | None = None  # mikrofon ADI; "" = sistem varsayılanı


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
    x_training_mode: str | None = Header(default=None, alias="X-Training-Mode"),
):
    from .parsers import should_save_pending_wav
    # JWT sets request.state; fall back to X-User-ID header for local mode compat
    state_user_id = getattr(request.state, "user_id", None)
    user_id = state_user_id or x_user_id or None
    tenant_id = getattr(request.state, "tenant_id", "default") or "default"

    save_pending_wav = should_save_pending_wav(x_training_mode)

    try:
        result = await svc.stop(
            user_id=user_id,
            tenant_id=tenant_id,
            active_app=x_active_app or None,
            window_title=x_window_title or None,
            selected_text=x_selected_text or None,
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
        input_device=config.input_device,
    )
    result = await apply_config(
        config=svc_config,
        svc=svc,
        app_state=request.app.state,
        backend_mode=_BACKEND_MODE,
        user_id=user_id,
        tenant_id=tenant_id,
    )
    return dataclasses.asdict(result)


@router.get("/history")
async def history(
    request: Request,
    limit: int = Query(default=100, le=1000),
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


@router.delete("/history/{record_id}")
async def delete_history_item(record_id: int, request: Request):
    from ..db import delete_transcription_by_id
    tenant_id = getattr(request.state, "tenant_id", "default") or "default"
    deleted = await delete_transcription_by_id(record_id, tenant_id)
    if not deleted:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not found")
    return {"status": "deleted", "id": record_id}


@router.delete("/history", dependencies=[require_role("admin")])
async def delete_history(request: Request):
    from ..services.history_service import wipe_history
    tenant_id = getattr(request.state, "tenant_id", "default") or "default"
    user_id = getattr(request.state, "user_id", "") or ""
    await wipe_history(tenant_id=tenant_id, user_id=user_id)
    return {"status": "cleared"}


def _user_id(request: Request, x_user_id: str | None) -> str:
    """JWT claim takes priority over X-User-ID header (backward compat fallback)."""
    return getattr(request.state, "user_id", None) or x_user_id or ""


# ------------------------------------------------------------------
# Dictionary (Katman 1)
# ------------------------------------------------------------------

class DictionaryEntryRequest(BaseModel):
    trigger: str
    replacement: str
    scope: str = "personal"


@router.get("/dictionary")
async def get_dict(
    request: Request,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    from ..services.dictionary_service import list_dictionary
    return await list_dictionary(user_id=_user_id(request, x_user_id))


@router.post("/dictionary")
async def add_dict_entry(
    body: DictionaryEntryRequest,
    request: Request,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    from ..services.dictionary_service import create_dictionary_entry
    try:
        return await create_dictionary_entry(
            trigger=body.trigger,
            replacement=body.replacement,
            user_id=_user_id(request, x_user_id),
            scope=body.scope,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/dictionary/bundle")
async def load_dict_bundle():
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


@router.post("/dictionary/learn")
async def learn_dictionary(
    request: Request,
    svc=Depends(get_service),
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    """User-triggered: scan recent transcriptions and learn recurring Whisper
    misrecognitions into the smart dictionary. Returns {"added", "busy"}.

    Heavy (loads the LLM if correction is off) — runs only when the user asks,
    so it never blocks a dictation on the single MLX worker.
    """
    tenant_id = getattr(request.state, "tenant_id", "default")
    return await svc.learn_now(_user_id(request, x_user_id), tenant_id)


@router.delete("/dictionary/{entry_id}")
async def delete_dict_entry(
    entry_id: int,
    request: Request,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    from ..services.dictionary_service import remove_dictionary_entry
    try:
        await remove_dictionary_entry(entry_id=entry_id, user_id=_user_id(request, x_user_id))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": "deleted", "id": entry_id}


# ------------------------------------------------------------------
# Feedback (training signal)
# ------------------------------------------------------------------

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
    user_id = getattr(request.state, "user_id", None)
    tenant_id = getattr(request.state, "tenant_id", "default") or "default"
    try:
        await _record_feedback(
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
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "ok"}
