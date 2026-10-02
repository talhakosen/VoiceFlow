"""Is a dictionary trigger a real Turkish word? Guards auto-generated entries.

Otomatik üretilen sözlük kayıtları (IT bundle, kod indeksleme, öğrenme) gerçek
Türkçe kelimeleri ikame etmemeli: "diye → DI'ye", "ekran → Screen" her diktede
uygulanıp metni bozuyordu. Manuel kayıtlar bu korumanın dışında.

Kelime listesi: core/data/turkish_words.txt — ISSAI insan transkriptlerinden,
`ml/dictionary/build_turkish_wordlist.py` ile üretilir.
"""

import re
from functools import lru_cache
from pathlib import Path

_WORDS_PATH = Path(__file__).parent / "data" / "turkish_words.txt"
_WORD = re.compile(r"[a-zçğıöşü]+")


def tr_lower(text: str) -> str:
    """Turkish-aware lowercase: str.lower() maps I → i, Turkish needs I → ı."""
    return text.replace("İ", "i").replace("I", "ı").lower()


@lru_cache(maxsize=1)
def _words() -> frozenset[str]:
    return frozenset(_WORDS_PATH.read_text(encoding="utf-8").split())


def is_turkish_phrase(trigger: str) -> bool:
    """True when every word of the trigger is a common Turkish word."""
    words = _WORD.findall(tr_lower(trigger))
    return bool(words) and all(w in _words() for w in words)


def without_turkish_triggers(pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Drop (trigger, replacement) pairs that would rewrite a real Turkish word.

    Identity entries ("alt → Alt") are kept: they change at most the case.
    """
    return [
        (t, r) for t, r in pairs
        if not is_turkish_phrase(t) or tr_lower(t) == tr_lower(r)
    ]
