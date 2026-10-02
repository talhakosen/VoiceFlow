"""TrainingDataService — pending WAV file management (training mode)."""

import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_SAMPLE_RATE = 16000


async def save_pending_wav(
    audio_data,
    raw_text: str,
    pending_dir: Path,
    sample_rate: int = _SAMPLE_RATE,
) -> str | None:
    """Save a pending WAV for later labelling. Returns wav_path or None on error."""
    if not raw_text.strip():
        return None

    try:
        import soundfile as sf

        pending_dir.mkdir(parents=True, exist_ok=True)
        ts = int(time.time() * 1000)
        pending_wav = pending_dir / f"{ts}.wav"
        sf.write(str(pending_wav), audio_data, sample_rate)
        logger.info("Pending WAV saved: %s", pending_wav.name)
        return str(pending_wav)
    except Exception as exc:
        logger.warning("Pending WAV save failed: %s", exc)
        return None
