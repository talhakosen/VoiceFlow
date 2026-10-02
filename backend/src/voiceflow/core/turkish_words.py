"""Is a dictionary trigger a real Turkish word? Guards auto-generated entries.

Otomatik üretilen sözlük kayıtları (IT bundle, kod indeksleme, öğrenme) gerçek
Türkçe kelimeleri ikame etmemeli: "diye → DI'ye", "ekran → Screen" her diktede
uygulanıp metni bozuyordu. Manuel kayıtlar bu korumanın dışında.

Kelime listesi: core/data/turkish_words.txt — ISSAI insan transkriptlerinden,
`ml/dictionary/build_turkish_wordlist.py` ile üretilir. ISSAI haber dili olduğu
için teknik bağlamdaki Türkçe kelimeler (buton, panel) turkish_words_extra.txt'de.
"""

import re
from functools import lru_cache
from pathlib import Path

_DATA = Path(__file__).parent / "data"
_WORD_FILES = ("turkish_words.txt", "turkish_words_extra.txt")

# Çekim ekleri — "şifreyi" listede yok ama "şifre" + "yi" Türkçe.
_SUFFIXES = (
    "ı i u ü yı yi yu yü a e ya ye da de ta te dan den tan ten ın in un ün "
    "nın nin nun nün la le yla yle lar ler ları leri lara lere larda lerde "
    "lerin ların sı si su sü ndan nden nda nde na ne nı ni nu nü"
).split()
_MIN_STEM = 4  # kısa kökler ("ses", "alt") ek ayırmada çok fazla yanlış eşleşir
_WORD = re.compile(r"[a-zçğıöşü]+")


def tr_lower(text: str) -> str:
    """Turkish-aware lowercase: str.lower() maps I → i, Turkish needs I → ı."""
    return text.replace("İ", "i").replace("I", "ı").lower()


@lru_cache(maxsize=1)
def _words() -> frozenset[str]:
    words: set[str] = set()
    for name in _WORD_FILES:
        for line in (_DATA / name).read_text(encoding="utf-8").splitlines():
            if line and not line.startswith("#"):
                words.add(line.strip())
    return frozenset(words)


def _is_turkish_word(word: str) -> bool:
    if word in _words():
        return True
    return any(
        word.endswith(s) and len(word) - len(s) >= _MIN_STEM and word[: -len(s)] in _words()
        for s in _SUFFIXES
    )


def is_turkish_phrase(trigger: str) -> bool:
    """True when every word of the trigger is a common Turkish word (or its inflection)."""
    words = _WORD.findall(tr_lower(trigger))
    return bool(words) and all(_is_turkish_word(w) for w in words)


def without_turkish_triggers(pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Drop (trigger, replacement) pairs that would rewrite a real Turkish word.

    Identity entries ("alt → Alt") are kept: they change at most the case.
    """
    return [
        (t, r) for t, r in pairs
        if not is_turkish_phrase(t) or tr_lower(t) == tr_lower(r)
    ]
