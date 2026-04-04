"""Dictionary post-processing — Aho-Corasick substitution pass.

Applied after Whisper transcription, before LLM correction.

Algorithm: Aho-Corasick automaton — builds a trie over all triggers once,
then scans the text in a single O(|text|) pass instead of O(N×|text|)
regex loops. Critical for large bundles (50K+ entries).

Phonetic dictionary format (K4-P1):
  trigger = phonetic spelling (one or more words), e.g. "ant row pick"
  replacement = correct term, e.g. "Anthropic"
"""

import re
from functools import lru_cache

try:
    import ahocorasick
    _HAS_AC = True
except ImportError:
    _HAS_AC = False


def _build_automaton(entries: list[dict]):
    """Build Aho-Corasick automaton from dictionary entries.

    Longer triggers win over shorter ones at the same position
    (stored as (len, replacement) so max() picks longest match).
    """
    A = ahocorasick.Automaton()
    for entry in entries:
        trigger = entry.get("trigger", "").strip().lower()
        replacement = entry.get("replacement", "").strip()
        if not trigger or not replacement:
            continue
        # Store (trigger_len, replacement); if same key exists, longest wins
        if A.exists(trigger):
            existing = A.get(trigger)
            if len(trigger) > existing[0]:
                A.add_word(trigger, (len(trigger), replacement))
        else:
            A.add_word(trigger, (len(trigger), replacement))
    A.make_automaton()
    return A


def _apply_aho_corasick(text: str, automaton) -> str:
    """Single-pass replacement using Aho-Corasick.

    Finds all non-overlapping matches (longest at each position),
    respects word boundaries, applies replacements right-to-left
    so offsets stay valid.
    """
    lower_text = text.lower()
    matches = []  # (start, end_inclusive, replacement)

    for end_idx, (tlen, replacement) in automaton.iter(lower_text):
        start_idx = end_idx - tlen + 1
        # Word-boundary check
        before_ok = (start_idx == 0 or not lower_text[start_idx - 1].isalnum())
        after_ok = (end_idx == len(lower_text) - 1 or not lower_text[end_idx + 1].isalnum())
        if before_ok and after_ok:
            matches.append((start_idx, end_idx, replacement))

    if not matches:
        return text

    # Resolve overlaps: greedy left-to-right, longest match wins
    matches.sort(key=lambda m: (m[0], -(m[1] - m[0])))
    non_overlapping = []
    last_end = -1
    for start, end, repl in matches:
        if start > last_end:
            non_overlapping.append((start, end, repl))
            last_end = end

    # Apply right-to-left so string indices stay valid
    result = list(text)
    for start, end, repl in reversed(non_overlapping):
        result[start:end + 1] = list(repl)

    return "".join(result)


def _apply_regex_fallback(text: str, entries: list[dict]) -> str:
    """Fallback O(N×M) regex path (used when pyahocorasick not available)."""
    sorted_entries = sorted(
        entries,
        key=lambda e: len(e.get("trigger", "")),
        reverse=True,
    )

    def _pass(t: str) -> str:
        for entry in sorted_entries:
            trigger = entry.get("trigger", "").strip()
            replacement = entry.get("replacement", "").strip()
            if not trigger or not replacement:
                continue
            pattern = r"(?<!\w)" + re.escape(trigger) + r"(?!\w)"
            t = re.sub(pattern, replacement, t, flags=re.IGNORECASE)
        return t

    return _pass(_pass(text))


_automaton_cache: tuple | None = None  # (content_hash, automaton)


def _entries_hash(entries: list[dict]) -> int:
    """Fast hash of entries content — for cache invalidation."""
    return hash(tuple(
        (e.get("trigger", ""), e.get("replacement", ""))
        for e in entries
    ))


def apply_dictionary(text: str, entries: list[dict]) -> str:
    """Replace trigger words/phrases with their replacements.

    Uses Aho-Corasick if available (O(|text|)), falls back to
    regex loop (O(N×|text|)) otherwise.

    Automaton is cached by content hash — rebuilt only when the
    dictionary changes (bundle load, user edit, etc.).
    """
    if not entries or not text:
        return text

    if _HAS_AC:
        global _automaton_cache
        h = _entries_hash(entries)
        if _automaton_cache is None or _automaton_cache[0] != h:
            _automaton_cache = (h, _build_automaton(entries))
        automaton = _automaton_cache[1]
        # Two passes: second pass catches chains (e.g. expanded term triggers another)
        text = _apply_aho_corasick(text, automaton)
        text = _apply_aho_corasick(text, automaton)
        return text
    else:
        return _apply_regex_fallback(text, entries)
