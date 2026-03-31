"""Dictionary post-processing — word-boundary substitution pass.

Applied after Whisper transcription, before LLM correction.

Phonetic dictionary format (K4-P1):
  trigger = phonetic spelling (one or more words), e.g. "ant row pick"
  replacement = correct term, e.g. "Anthropic"
  Trigger and replacement are separated by " = " in the trigger field when using
  the phonetic convention, but the standard trigger/replacement fields also work
  for multi-word phonetic entries.
"""

import re


def apply_dictionary(text: str, entries: list[dict]) -> str:
    """Replace trigger words/phrases with their replacements.

    Supports both single-word and multi-word (phonetic) triggers:
    - Single-word: "apvyumodel" → "AppViewModel"
    - Phonetic multi-word: "ant row pick" → "Anthropic"

    Matching rules:
    - Word-boundary match (\\b) prevents partial matches for single words
    - Multi-word triggers use word boundary only at start and end of the phrase
    - Case-insensitive match; replacement is used as-is
    - Skips entries with empty trigger or replacement
    - Longer triggers are matched first to avoid partial clobbering
    """
    if not entries:
        return text

    # Sort by trigger length descending so longer (more specific) phrases match first
    sorted_entries = sorted(
        entries,
        key=lambda e: len(e.get("trigger", "")),
        reverse=True,
    )

    for entry in sorted_entries:
        trigger = entry.get("trigger", "").strip()
        replacement = entry.get("replacement", "").strip()
        if not trigger or not replacement:
            continue
        # Use word boundary anchors around the full trigger phrase
        pattern = r"(?<!\w)" + re.escape(trigger) + r"(?!\w)"
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    return text
