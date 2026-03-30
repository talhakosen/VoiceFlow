"""Dictionary post-processing — word-boundary substitution pass.

Applied after Whisper transcription, before LLM correction.
"""

import re


def apply_dictionary(text: str, entries: list[dict]) -> str:
    """Replace trigger words/phrases with their replacements.

    - Word-boundary match (re.sub with \\b) — avoids partial matches
    - Case-insensitive match; preserves original casing of replacement
    - Skips entries with empty trigger or replacement
    - Short-circuits if entries list is empty
    """
    if not entries:
        return text

    for entry in entries:
        trigger = entry.get("trigger", "").strip()
        replacement = entry.get("replacement", "").strip()
        if not trigger or not replacement:
            continue
        pattern = r"\b" + re.escape(trigger) + r"\b"
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    return text
