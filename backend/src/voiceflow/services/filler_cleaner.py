"""Deterministic Turkish filler word remover.

Runs after dictionary substitution, before LLM correction.
Engineering mode: skipped entirely (technical terms preserved as-is).

Pipeline order: Whisper → Dictionary → FillerCleaner → Snippets → LLM
"""

import re

# ── Words that "protect" şey/yani — if preceded, leave them ─────────────────
# "bir şey", "hiç şey", "her şey", "ne şey", "başka şey" → keep (noun)
_SEY_PROTECT_RE = re.compile(
    r'\b(bir|hiç|her|ne|başka|herhangi|bazı|çok|az|o)\s+şey\b',
    re.IGNORECASE,
)

# ── Multi-word filler chains (remove first) ──────────────────────────────────
_CHAIN_RE = re.compile(
    r'\b(yani\s+şey|şey\s+işte|hani\s+yani|işte\s+yani|yani\s+hani'
    r'|şey\s+yani|hani\s+şey|yani\s+yani|şey\s+şey)[,\s]*',
    re.IGNORECASE,
)

# ── Sentence starters ────────────────────────────────────────────────────────
_STARTER_RE = re.compile(
    r'(?:(?:^|(?<=[.!?])\s*))(şey|yani|hani|ee+|aa+|hmm?|ımm?)[,\s]+',
    re.IGNORECASE,
)

# ── "yani" between commas: "X, yani, Y" → "X, Y" ───────────────────────────
_YANI_BETWEEN_COMMAS_RE = re.compile(
    r',\s*yani\s*,',
    re.IGNORECASE,
)

# ── "yani" after comma before content (softener): "gerekiyor, yani müsaitsen" ─
# Protect: digit context before comma ("500 kişi, yani yarısı") → keep
_YANI_NUMBER_PROTECT_RE = re.compile(
    r'(\d[\d\w]*\s+\w+),\s*yani\s+',
    re.IGNORECASE,
)
_YANI_SOFTENER_RE = re.compile(
    r',\s*yani\s+(?=\w)',
    re.IGNORECASE,
)

# ── "yani" mid-sentence between spaces (no commas): "var yani şimdi" ─────────
_YANI_MID_RE = re.compile(
    r'(?<=[a-zA-ZğüşıöçĞÜŞİÖÇ])\s+yani\s+(?=[a-zA-ZğüşıöçĞÜŞİÖÇ])',
    re.IGNORECASE,
)

# ── Sentence-final yani/şey/hani (before . ! ? or end) ─────────────────────
_FINAL_RE = re.compile(
    r',?\s+\b(yani|şey|hani)\b\s*(?=[.!?]|$)',
    re.IGNORECASE,
)

# ── Standalone "şey" mid-sentence (not protected) ───────────────────────────
# Matches "şey" surrounded by spaces or commas, not preceded by protector words
_SEY_STANDALONE_RE = re.compile(
    r'(?<![a-zA-ZğüşıöçĞÜŞİÖÇ])\bşey\b(?![a-zA-ZğüşıöçĞÜŞİÖÇ])',
    re.IGNORECASE,
)

# ── Hesitation sounds ────────────────────────────────────────────────────────
_HESITATION_RE = re.compile(
    r'(?<![a-zA-ZğüşıöçĞÜŞİÖÇ])\b(ee+|aa+|hmm?|ımm?)\b(?![a-zA-ZğüşıöçĞÜŞİÖÇ])',
    re.IGNORECASE,
)


def _protect_sey(text: str) -> tuple[str, list[str]]:
    """Replace protected 'şey' phrases with placeholders before cleaning."""
    placeholders = []
    def _replace(m):
        placeholders.append(m.group(0))
        return f'__SEY_{len(placeholders)-1}__'
    return _SEY_PROTECT_RE.sub(_replace, text), placeholders


def _restore_sey(text: str, placeholders: list[str]) -> str:
    for i, original in enumerate(placeholders):
        text = text.replace(f'__SEY_{i}__', original)
    return text


def _normalize(text: str) -> str:
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = re.sub(r'\s*,\s*,+', ',', text)    # double commas
    text = re.sub(r'^[,\s]+', '', text)        # leading junk
    text = re.sub(r'[,\s]+$', '.', text) if text and text[-1] not in '.!?' else re.sub(r'[,\s]+$', '', text)
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    return text.strip()


def clean_fillers(text: str) -> str:
    """Remove Turkish filler words deterministically.

    Skip this function entirely for engineering mode.
    """
    if not text or not text.strip():
        return text

    # Protect meaningful "bir şey", "her şey" etc. from being cleaned
    text, sey_slots = _protect_sey(text)

    # Protect "500 kişi, yani yarısı" → placeholder
    number_protects = []
    def _save_number_yani(m):
        number_protects.append(m.group(0))
        return f'__NUMYANI_{len(number_protects)-1}__'
    text = _YANI_NUMBER_PROTECT_RE.sub(_save_number_yani, text)

    text = _CHAIN_RE.sub(' ', text)
    text = _STARTER_RE.sub('', text)
    text = _YANI_BETWEEN_COMMAS_RE.sub(',', text)
    text = _YANI_SOFTENER_RE.sub(', ', text)
    text = _YANI_MID_RE.sub(' ', text)
    text = _FINAL_RE.sub('', text)
    text = _SEY_STANDALONE_RE.sub('', text)
    text = _HESITATION_RE.sub('', text)

    # Restore number-protected yani phrases
    for i, original in enumerate(number_protects):
        text = text.replace(f'__NUMYANI_{i}__', original)

    text = _restore_sey(text, sey_slots)
    text = _normalize(text)

    return text
