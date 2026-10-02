"""Training routes — /training/* endpoints (training-mode correction pairs)."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .auth import verify_api_key
from ..core.config import USER_CORRECTIONS_DIR

logger = logging.getLogger(__name__)

training_router = APIRouter(dependencies=[Depends(verify_api_key)])

_USER_CORRECTIONS_DIR = USER_CORRECTIONS_DIR
_USER_CORRECTIONS_JSONL = _USER_CORRECTIONS_DIR.parent / "corrections.jsonl"
_PENDING_DIR = USER_CORRECTIONS_DIR  # pending WAVs live in USER_CORRECTIONS_DIR

# ── Schemas ──────────────────────────────────────────────────────────────────

class SaveCorrectionRequest(BaseModel):
    wav_path: str
    whisper_text: str
    corrected_text: str


class DeletePendingWavRequest(BaseModel):
    wav_path: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@training_router.post("/training/save-correction")
async def save_user_correction(req: SaveCorrectionRequest) -> dict:
    """Keep pending WAV and append (wav, whisper, corrected) pair to JSONL."""
    from ..services.training_service import save_correction
    try:
        return await save_correction(
            wav_path_str=req.wav_path,
            whisper_text=req.whisper_text,
            corrected_text=req.corrected_text,
            corrections_dir=_USER_CORRECTIONS_DIR,
            corrections_jsonl=_USER_CORRECTIONS_JSONL,
            pending_dir=_PENDING_DIR,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@training_router.delete("/training/pending-wav")
async def delete_pending_wav_route(req: DeletePendingWavRequest) -> dict:
    """Delete a pending WAV (user dismissed or approved without editing)."""
    from ..services.training_service import delete_pending_wav
    try:
        return await delete_pending_wav(wav_path_str=req.wav_path, pending_dir=_PENDING_DIR)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
