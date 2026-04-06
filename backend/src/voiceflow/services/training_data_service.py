"""TrainingDataService — IT dataset and pending WAV file management."""

import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_SAMPLE_RATE = 16000


async def save_it_recording(
    audio_data,
    it_dataset_index: int,
    raw_text: str,
    wav_dir: Path,
    sample_rate: int = _SAMPLE_RATE,
) -> str | None:
    """Save IT dataset WAV + DB recording. Returns wav_path or None on skip/error."""
    from ..db import get_training_sentence_by_id, save_training_recording

    if not raw_text.strip():
        logger.warning(
            "IT recording skipped: empty/hallucination text for sentence_id=%d", it_dataset_index
        )
        return None

    try:
        import soundfile as sf

        wav_dir.mkdir(parents=True, exist_ok=True)
        ts = int(time.time() * 1000)
        wav_path = wav_dir / f"{it_dataset_index:05d}_{ts}.wav"
        sf.write(str(wav_path), audio_data, sample_rate)
        logger.info("IT dataset WAV saved: %s", wav_path)

        sentence = await get_training_sentence_by_id(it_dataset_index)
        training_set = sentence["training_set"] if sentence else "it_dataset"
        await save_training_recording(
            sentence_id=it_dataset_index,
            training_set=training_set,
            wav_path=str(wav_path),
            whisper_out=raw_text,
        )
        logger.info("IT recording saved: id=%d whisper='%s'", it_dataset_index, raw_text[:60])
        return str(wav_path)
    except Exception as exc:
        logger.warning("IT dataset save failed: %s", exc)
        return None


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
