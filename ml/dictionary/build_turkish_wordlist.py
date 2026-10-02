"""Türkçe kelime listesi üret — sözlük tetikleyicisi gerçek Türkçe kelime mi kontrolü için.

Kaynak: ISSAI ground-truth transkriptleri (insan yazımı, ~164K cümle).
Çıktı:  backend/src/voiceflow/core/data/turkish_words.txt (frekansı >= MIN_FREQ olanlar)

Kullanım: python ml/dictionary/build_turkish_wordlist.py
"""
import collections
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "ml/whisper/datasets/issai/issai_pairs_clean.jsonl"
OUT = ROOT / "backend/src/voiceflow/core/data/turkish_words.txt"
MIN_FREQ = 5  # nadir kelimeler = yazım hatası / özel isim / yabancı terim olabilir

_WORD = re.compile(r"[a-zçğıöşü]+")


def tr_lower(s: str) -> str:
    return s.replace("İ", "i").replace("I", "ı").lower()


counts: collections.Counter[str] = collections.Counter()
with SRC.open(encoding="utf-8") as f:
    for line in f:
        counts.update(_WORD.findall(tr_lower(json.loads(line)["output"])))

words = sorted(w for w, n in counts.items() if n >= MIN_FREQ and len(w) >= 2)
OUT.write_text("\n".join(words) + "\n", encoding="utf-8")
print(f"{len(words)} kelime → {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB)")
