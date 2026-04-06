"""TrainingService — IT dataset sentence/recording management business logic."""

import asyncio
import base64
import json
import logging
import time
from pathlib import Path

from ..db import (
    import_training_sentences,
    get_random_unrecorded_sentence,
    get_training_sentence_by_id,
    save_training_recording,
    delete_training_recording,
    get_recordings_for_sentence,
    get_recorded_sentences,
)

logger = logging.getLogger(__name__)

_MAX_AUDIO_BYTES = 50 * 1024 * 1024  # 50 MB


def _assert_safe_path(path: Path, root: Path) -> None:
    """Raise ValueError if `path` is not under `root` (path traversal guard)."""
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        raise ValueError(f"Path outside allowed directory: {path}")


# ── Sentence import ──────────────────────────────────────────────────────────

async def ensure_sentences_imported(training_set: str, data_path: Path) -> None:
    """Import sentences from JSONL on first run (idempotent). File I/O off event loop."""
    if not data_path.exists():
        return

    def _read() -> list[dict]:
        with open(data_path) as f:
            return [json.loads(line) for line in f if line.strip()]

    loop = asyncio.get_running_loop()
    sentences = await loop.run_in_executor(None, _read)
    if not sentences:
        return
    n = await import_training_sentences(training_set, sentences)
    if n > 0:
        logger.info("Imported %d training sentences for '%s'", n, training_set)


# ── Sentence queries ─────────────────────────────────────────────────────────

async def next_sentence(training_set: str, data_path: Path) -> dict | None:
    """Return a random unrecorded sentence with its existing recordings."""
    await ensure_sentences_imported(training_set, data_path)
    row = await get_random_unrecorded_sentence(training_set)
    if row is None:
        return None
    recs = await get_recordings_for_sentence(row["id"])
    return {**row, "recordings": recs}


async def recorded_sentences(training_set: str) -> list[dict]:
    """All sentences with at least one recording."""
    return await get_recorded_sentences(training_set)


# ── Recording lifecycle ───────────────────────────────────────────────────────

async def record_pair(
    sentence_id: int,
    whisper_output: str,
    audio_b64: str | None,
    recordings_dir: Path,
) -> dict:
    """Save a WAV (if provided) and persist the DB record. Raises ValueError/LookupError."""
    sentence = await get_training_sentence_by_id(sentence_id)
    if sentence is None:
        raise LookupError("Invalid sentence id")

    wav_path_str = ""
    if audio_b64:
        if len(audio_b64) > int(_MAX_AUDIO_BYTES * 1.37):  # base64 ~37% overhead
            raise ValueError("Audio file too large (max 50 MB)")

        audio_bytes = base64.b64decode(audio_b64)
        recordings_dir.mkdir(parents=True, exist_ok=True)
        ts = int(time.time() * 1000)
        wav_path = recordings_dir / f"{sentence_id:05d}_{ts}.wav"

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, wav_path.write_bytes, audio_bytes)
        wav_path_str = str(wav_path)

    await save_training_recording(
        sentence_id=sentence_id,
        training_set=sentence["training_set"],
        wav_path=wav_path_str,
        whisper_out=whisper_output,
    )
    logger.info("IT recording saved: sentence_id=%d whisper='%s'", sentence_id, whisper_output[:60])
    return {"status": "ok"}


async def delete_pair(wav_path_str: str, recordings_dir: Path) -> dict:
    """Delete WAV file and DB record. Raises ValueError on path traversal."""
    wav = Path(wav_path_str)
    _assert_safe_path(wav, recordings_dir)

    loop = asyncio.get_running_loop()
    if wav.exists():
        await loop.run_in_executor(None, wav.unlink)
        logger.info("IT WAV deleted: %s", wav)
    await delete_training_recording(wav_path_str)
    return {"status": "ok"}


# ── User corrections ──────────────────────────────────────────────────────────

async def save_correction(
    wav_path_str: str,
    whisper_text: str,
    corrected_text: str,
    corrections_dir: Path,
    corrections_jsonl: Path,
    pending_dir: Path,
) -> dict:
    """Move pending WAV to corrections dir and append to JSONL. Raises ValueError/FileNotFoundError."""
    wav = Path(wav_path_str)
    _assert_safe_path(wav, pending_dir)

    loop = asyncio.get_running_loop()
    if not await loop.run_in_executor(None, wav.exists):
        raise FileNotFoundError("WAV not found")

    corrections_dir.mkdir(parents=True, exist_ok=True)
    final_path = corrections_dir / wav.name
    await loop.run_in_executor(None, wav.rename, final_path)

    record = json.dumps({
        "audio": str(final_path),
        "whisper_out": whisper_text,
        "corrected": corrected_text,
    }, ensure_ascii=False) + "\n"

    def _append() -> None:
        with open(corrections_jsonl, "a", encoding="utf-8") as f:
            f.write(record)

    await loop.run_in_executor(None, _append)
    logger.info("User correction saved: %s → '%s'", final_path.name, corrected_text[:60])
    return {"status": "ok", "wav_path": str(final_path)}


async def delete_pending_wav(wav_path_str: str, pending_dir: Path) -> dict:
    """Delete a pending WAV. Raises ValueError on path traversal."""
    wav = Path(wav_path_str)
    _assert_safe_path(wav, pending_dir)

    loop = asyncio.get_running_loop()
    if await loop.run_in_executor(None, wav.exists):
        await loop.run_in_executor(None, wav.unlink)
        logger.info("Pending WAV deleted: %s", wav.name)
    return {"status": "ok"}
