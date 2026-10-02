"""TrainingService — training-mode correction pairs (pending WAV + corrected text)."""

import asyncio
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _assert_safe_path(path: Path, root: Path) -> None:
    """Raise ValueError if `path` is not under `root` (path traversal guard)."""
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        raise ValueError(f"Path outside allowed directory: {path}")


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
