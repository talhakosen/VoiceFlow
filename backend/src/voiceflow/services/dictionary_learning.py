"""Background dictionary learning.

Mines recurring Whisper misrecognitions from the user's own raw transcriptions
and adds them to the smart dictionary, so they get fixed deterministically
(Aho-Corasick, ~microseconds) at dictation time — no LLM on the live path.

Runs in the background after every N dictations (see RecordingService). The LLM
is used ONLY here, offline, never blocking a dictation.

Quality guards (all must pass before a pair is stored):
  1. Hallucination guard — the "wrong" word must actually occur in the source
     texts (the LLM can't invent corrections for words that weren't said).
  2. Frequency — must occur at least `min_freq` times (skip one-off noise).
  3. Phonetic — "wrong" must plausibly sound like "correct" (skip semantic
     rewrites that aren't speech-to-text errors).
"""

from __future__ import annotations

import asyncio
import functools
import json
import logging

import jellyfish

from ..db import bulk_add_smart_entries, get_history

logger = logging.getLogger(__name__)

LEARN_SYSTEM_PROMPT = (
    "You are a proofreader for Turkish speech-to-text output. The transcriber "
    "sometimes mishears domain-specific or English technical terms — e.g. "
    "'deploy'→'diploy', 'commit'→'komut', 'branch'→'brençh', 'cache'→'keş'. "
    "Given several raw transcriptions, find ONLY clear misrecognitions of real "
    "technical or proper terms. Respond with a JSON array of objects: "
    '{"wrong": "<exactly as written>", "correct": "<intended term>"}. '
    "Single words only, high confidence, phonetically similar. No prose. "
    "If nothing is clearly wrong, respond with []."
)


def extract_pairs(llm_output: str) -> list[tuple[str, str]]:
    """Parse the LLM's JSON array into (wrong, correct) pairs.

    Tolerant of prose wrapped around the JSON array.
    """
    start, end = llm_output.find("["), llm_output.rfind("]")
    if start < 0 or end <= start:
        return []
    try:
        data = json.loads(llm_output[start : end + 1])
    except (json.JSONDecodeError, ValueError):
        return []
    if not isinstance(data, list):
        return []

    pairs: list[tuple[str, str]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        wrong = str(item.get("wrong", "")).strip()
        correct = str(item.get("correct", "")).strip()
        if wrong and correct and wrong.lower() != correct.lower():
            pairs.append((wrong, correct))
    return pairs


def phonetically_similar(wrong: str, correct: str) -> bool:
    """True if the two words plausibly sound alike.

    Guards against the LLM proposing semantic 'corrections' that are not
    actual speech-to-text errors.
    """
    w, c = wrong.lower().strip(), correct.lower().strip()
    if not w or not c:
        return False
    if jellyfish.metaphone(w) == jellyfish.metaphone(c):
        return True
    return jellyfish.jaro_winkler_similarity(w, c) >= 0.82


def filter_pairs(
    pairs: list[tuple[str, str]], texts: list[str], min_freq: int = 2
) -> list[tuple[str, str]]:
    """Apply the hallucination, frequency and phonetic guards.

    Returns (trigger, replacement) pairs ready for the smart dictionary, with
    the trigger lower-cased (Aho-Corasick matches case-insensitively) and
    deduped by trigger.
    """
    blob = " ".join(texts).lower()
    out: dict[str, str] = {}
    for wrong, correct in pairs:
        w = wrong.lower()
        if blob.count(w) < min_freq:  # hallucination + frequency guard
            continue
        if not phonetically_similar(wrong, correct):  # phonetic guard
            continue
        out.setdefault(w, correct)
    return list(out.items())


async def learn_from_history(
    user_id: str | None,
    tenant_id: str,
    corrector,
    executor,
    *,
    scan_limit: int = 30,
    min_freq: int = 2,
) -> int:
    """Scan recent raw transcriptions, learn misrecognitions, add to smart dict.

    Returns the number of new entries added. No-op if the corrector cannot do a
    free-form completion (e.g. remote/passthrough correctors) or there is no
    history yet. The LLM call runs on `executor` (the single MLX worker).
    """
    if user_id is None or not hasattr(corrector, "complete"):
        return 0

    rows = await get_history(limit=scan_limit, user_id=user_id, tenant_id=tenant_id)
    texts = [r["raw_text"] for r in rows if r.get("raw_text")]
    if not texts:
        return 0

    user_msg = "\n".join(f"- {t}" for t in texts)
    loop = asyncio.get_running_loop()
    try:
        output = await loop.run_in_executor(
            executor, functools.partial(corrector.complete, LEARN_SYSTEM_PROMPT, user_msg, 400)
        )
    except Exception as e:
        logger.warning("Dictionary learning LLM call failed: %s", e)
        return 0

    pairs = filter_pairs(extract_pairs(output), texts, min_freq=min_freq)
    if not pairs:
        return 0

    added = await bulk_add_smart_entries(user_id, tenant_id, pairs, scope="learned")
    if added:
        logger.info("Dictionary learning added %d entries: %s", added, pairs)
    return added
