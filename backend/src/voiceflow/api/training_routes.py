"""Training routes — /it-dataset/* and /training/* endpoints."""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .auth import verify_api_key
from ..core.config import IT_DATASET_DIR, USER_CORRECTIONS_DIR

logger = logging.getLogger(__name__)

training_router = APIRouter(dependencies=[Depends(verify_api_key)])

_ML_ROOT = Path(__file__).parents[4] / "ml"
_IT_DATASET_PATH = _ML_ROOT / "whisper" / "datasets" / "it_dataset" / "whisper_sentences.jsonl"
_IT_TERMS_PATH = _ML_ROOT / "whisper" / "datasets" / "it_dataset" / "it_terms.jsonl"
_IT_RECORDINGS_DIR = IT_DATASET_DIR
_USER_CORRECTIONS_DIR = USER_CORRECTIONS_DIR
_USER_CORRECTIONS_JSONL = _USER_CORRECTIONS_DIR.parent / "corrections.jsonl"
_PENDING_DIR = USER_CORRECTIONS_DIR  # pending WAVs live in USER_CORRECTIONS_DIR

_TRAINING_DATA_PATHS: dict[str, Path] = {
    "it_dataset": _IT_DATASET_PATH,
    "it_terms": _IT_TERMS_PATH,
}


# ── Schemas ──────────────────────────────────────────────────────────────────

class ITRecording(BaseModel):
    whisper: str
    wav_path: str


class ITDatasetResponse(BaseModel):
    index: int
    total: int
    sentence: str
    persona: str | None = None
    scenario: str | None = None
    recordings: list[ITRecording] = []


class ITRecordRequest(BaseModel):
    index: int
    whisper_output: str
    audio_b64: str | None = None


class ITDeleteRequest(BaseModel):
    wav_path: str


class SaveCorrectionRequest(BaseModel):
    wav_path: str
    whisper_text: str
    corrected_text: str


class DeletePendingWavRequest(BaseModel):
    wav_path: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _row_to_response(row: dict) -> ITDatasetResponse:
    recs = row.get("recordings", [])
    return ITDatasetResponse(
        index=row["id"],
        total=row["total"],
        sentence=row["text"],
        persona=row.get("persona"),
        scenario=row.get("scenario"),
        recordings=[
            ITRecording(whisper=r.get("whisper_out") or r.get("whisper", ""), wav_path=r["wav_path"])
            for r in recs
        ],
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@training_router.get("/it-dataset/next")
async def get_next_it_sentence(offset: int = 0, training_set: str = "it_dataset") -> ITDatasetResponse:
    """Return a random unrecorded sentence."""
    from ..services.training_service import next_sentence
    row = await next_sentence(training_set, _TRAINING_DATA_PATHS.get(training_set, _IT_DATASET_PATH))
    if row is None:
        return ITDatasetResponse(index=-1, total=0, sentence="")
    return _row_to_response(row)


@training_router.get("/it-dataset/random")
async def get_random_it_sentence(training_set: str = "it_dataset") -> ITDatasetResponse:
    """Shuffle — return a different random unrecorded sentence."""
    from ..services.training_service import next_sentence
    row = await next_sentence(training_set, _TRAINING_DATA_PATHS.get(training_set, _IT_DATASET_PATH))
    if row is None:
        return ITDatasetResponse(index=-1, total=0, sentence="")
    return _row_to_response(row)


@training_router.post("/it-dataset/record")
async def record_it_pair(req: ITRecordRequest) -> dict:
    from ..services.training_service import record_pair
    try:
        return await record_pair(
            sentence_id=req.index,
            whisper_output=req.whisper_output,
            audio_b64=req.audio_b64,
            recordings_dir=_IT_RECORDINGS_DIR,
        )
    except LookupError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=413, detail=str(e))


@training_router.delete("/it-dataset/record")
async def delete_it_pair(req: ITDeleteRequest) -> dict:
    from ..services.training_service import delete_pair
    try:
        return await delete_pair(wav_path_str=req.wav_path, recordings_dir=_IT_RECORDINGS_DIR)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@training_router.get("/it-dataset/recorded")
async def get_recorded_it_sentences(training_set: str = "it_dataset") -> list[ITDatasetResponse]:
    """All sentences with at least one recording (Pratik tab)."""
    from ..services.training_service import recorded_sentences
    rows = await recorded_sentences(training_set)
    return [_row_to_response(r) for r in rows]


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
