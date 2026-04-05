"""recording/segmenter.py — Audio segmentation + per-segment transcription.

Splits audio by Cmd-held intervals, transcribes each segment separately,
injects symbol refs into Cmd-held segments.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from ..core.interfaces import AbstractTranscriber

logger = logging.getLogger(__name__)

# Single-thread executor for MLX operations (Metal GPU is not thread-safe)
_mlx_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mlx")

_SAMPLE_RATE = 16000
_MIN_CHUNK_SECONDS = 0.3  # skip chunks shorter than this (noise)


async def transcribe_segmented(
    audio_data,
    cmd_intervals: list[tuple[float, float]],
    transcriber: AbstractTranscriber,
    user_id: str,
    loop,
) -> tuple[str, str | None, float]:
    """Split audio by Cmd intervals, transcribe each part separately.

    Cmd-held segments → transcribe → inject_symbol_refs
    Normal segments   → transcribe → pass through

    Returns: (merged_text, language, total_duration_seconds)
    """
    from ..symbol import inject_symbol_refs

    total_samples = len(audio_data)
    total_duration = total_samples / _SAMPLE_RATE

    segments: list[tuple[float, float, bool]] = []
    prev = 0.0
    for s, e in sorted(cmd_intervals):
        s = max(0.0, min(s, total_duration))
        e = max(0.0, min(e, total_duration))
        if s > prev + _MIN_CHUNK_SECONDS:
            segments.append((prev, s, False))
        if e > s + _MIN_CHUNK_SECONDS:
            segments.append((s, e, True))
        prev = e
    if prev + _MIN_CHUNK_SECONDS < total_duration:
        segments.append((prev, total_duration, False))

    parts: list[str] = []
    detected_language: str | None = None

    for start, end, is_cmd in segments:
        chunk = audio_data[int(start * _SAMPLE_RATE): int(end * _SAMPLE_RATE)]
        if len(chunk) < int(_MIN_CHUNK_SECONDS * _SAMPLE_RATE):
            continue
        seg_result = await loop.run_in_executor(_mlx_executor, transcriber.transcribe, chunk)
        if not seg_result.text.strip():
            continue
        if detected_language is None and seg_result.language:
            detected_language = seg_result.language
        text = seg_result.text.strip()
        if is_cmd and user_id:
            text = await inject_symbol_refs(text, user_id)
            logger.info("Cmd segment injected: '%s'", text[:80])
        parts.append(text)

    return " ".join(parts), detected_language, total_duration
