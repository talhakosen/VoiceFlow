"""Training routes — /it-dataset/* and /training/* endpoints."""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from .auth import verify_api_key
from ..db import (
    import_training_sentences, get_random_unrecorded_sentence,
    get_training_sentence_by_id, save_training_recording,
    delete_training_recording, get_recordings_for_sentence, get_recorded_sentences,
)

logger = logging.getLogger(__name__)

training_router = APIRouter(dependencies=[Depends(verify_api_key)])

_MAX_AUDIO_BYTES = 50 * 1024 * 1024  # 50 MB

_ML_ROOT = Path(__file__).parents[4] / "ml"
_IT_DATASET_PATH = _ML_ROOT / "whisper" / "datasets" / "it_dataset" / "whisper_sentences.jsonl"
_IT_TERMS_PATH = _ML_ROOT / "whisper" / "datasets" / "it_dataset" / "it_terms.jsonl"
_IT_RECORDINGS_DIR = _ML_ROOT / "whisper" / "datasets" / "it_dataset" / "recordings"
_USER_CORRECTIONS_DIR = _ML_ROOT / "whisper" / "datasets" / "user_corrections"
_USER_CORRECTIONS_JSONL = _USER_CORRECTIONS_DIR / "corrections.jsonl"

_TRAINING_DATA_PATHS: dict[str, Path] = {
    "it_dataset": _IT_DATASET_PATH,
    "it_terms": _IT_TERMS_PATH,
}


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


async def _ensure_sentences_imported(training_set: str = "it_dataset") -> None:
    """Import sentences from JSONL on first run (idempotent — skips if already imported)."""
    data_path = _TRAINING_DATA_PATHS.get(training_set, _IT_DATASET_PATH)
    if not data_path.exists():
        return
    with open(data_path) as f:
        sentences = [json.loads(line) for line in f if line.strip()]
    if not sentences:
        return
    n = await import_training_sentences(training_set, sentences)
    if n > 0:
        logger.info("Imported %d training sentences for '%s'", n, training_set)


@training_router.get("/it-dataset/next")
async def get_next_it_sentence(offset: int = 0, training_set: str = "it_dataset") -> ITDatasetResponse:
    """Return a random unrecorded sentence. `offset` param kept for backwards compat (ignored)."""
    await _ensure_sentences_imported(training_set)
    row = await get_random_unrecorded_sentence(training_set)
    if row is None:
        return ITDatasetResponse(index=-1, total=0, sentence="")
    recs = await get_recordings_for_sentence(row["id"])
    return ITDatasetResponse(
        index=row["id"],
        total=row["total"],
        sentence=row["text"],
        persona=row["persona"],
        scenario=row["scenario"],
        recordings=[ITRecording(whisper=r["whisper_out"] or "", wav_path=r["wav_path"]) for r in recs],
    )


@training_router.get("/it-dataset/random")
async def get_random_it_sentence(training_set: str = "it_dataset") -> ITDatasetResponse:
    """Shuffle — return a different random unrecorded sentence."""
    await _ensure_sentences_imported(training_set)
    row = await get_random_unrecorded_sentence(training_set)
    if row is None:
        return ITDatasetResponse(index=-1, total=0, sentence="")
    recs = await get_recordings_for_sentence(row["id"])
    return ITDatasetResponse(
        index=row["id"],
        total=row["total"],
        sentence=row["text"],
        persona=row["persona"],
        scenario=row["scenario"],
        recordings=[ITRecording(whisper=r["whisper_out"] or "", wav_path=r["wav_path"]) for r in recs],
    )


@training_router.post("/it-dataset/record")
async def record_it_pair(req: ITRecordRequest, request: Request) -> dict:
    sentence = await get_training_sentence_by_id(req.index)
    if sentence is None:
        raise HTTPException(status_code=400, detail="Invalid sentence id")

    wav_path_str = ""
    import base64
    import time
    if req.audio_b64:
        if len(req.audio_b64) > int(_MAX_AUDIO_BYTES * 1.37):  # base64 ~37% overhead
            raise HTTPException(status_code=413, detail="Audio file too large (max 50 MB)")
        _IT_RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
        audio_bytes = base64.b64decode(req.audio_b64)
        ts = int(time.time() * 1000)
        wav_path = _IT_RECORDINGS_DIR / f"{req.index:05d}_{ts}.wav"
        wav_path.write_bytes(audio_bytes)
        wav_path_str = str(wav_path)

    await save_training_recording(
        sentence_id=req.index,
        training_set=sentence["training_set"],
        wav_path=wav_path_str,
        whisper_out=req.whisper_output,
    )
    logger.info("IT recording saved: sentence_id=%d whisper='%s'", req.index, req.whisper_output[:60])
    return {"status": "ok"}


@training_router.delete("/it-dataset/record")
async def delete_it_pair(req: ITDeleteRequest) -> dict:
    wav = Path(req.wav_path)
    if wav.exists():
        wav.unlink()
        logger.info("IT WAV deleted: %s", wav)
    await delete_training_recording(req.wav_path)
    return {"status": "ok"}


@training_router.get("/it-dataset/recorded")
async def get_recorded_it_sentences(training_set: str = "it_dataset") -> list[ITDatasetResponse]:
    """All sentences with at least one recording (Pratik tab)."""
    rows = await get_recorded_sentences(training_set)
    return [
        ITDatasetResponse(
            index=r["id"],
            total=r["total"],
            sentence=r["text"],
            persona=r["persona"],
            scenario=r["scenario"],
            recordings=[ITRecording(**rec) for rec in r["recordings"]],
        )
        for r in rows
    ]


@training_router.post("/training/save-correction")
async def save_user_correction(req: SaveCorrectionRequest) -> dict:
    """Keep pending WAV and append (wav, whisper, corrected) pair to JSONL."""
    wav = Path(req.wav_path)
    if not wav.exists():
        raise HTTPException(status_code=404, detail="WAV not found")

    final_dir = _USER_CORRECTIONS_DIR
    final_dir.mkdir(parents=True, exist_ok=True)
    final_path = final_dir / wav.name
    wav.rename(final_path)

    with open(_USER_CORRECTIONS_JSONL, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "audio": str(final_path),
            "whisper_out": req.whisper_text,
            "corrected": req.corrected_text,
        }, ensure_ascii=False) + "\n")

    logger.info("User correction saved: %s → '%s'", final_path.name, req.corrected_text[:60])
    return {"status": "ok", "wav_path": str(final_path)}


@training_router.delete("/training/pending-wav")
async def delete_pending_wav(req: DeletePendingWavRequest) -> dict:
    """Delete a pending WAV (user dismissed or approved without editing)."""
    wav = Path(req.wav_path)
    if wav.exists():
        wav.unlink()
        logger.info("Pending WAV deleted: %s", wav.name)
    return {"status": "ok"}
