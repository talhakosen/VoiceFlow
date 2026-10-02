"""Dikte eval seti — kayıt seçimi + Whisper ön-doldurma.

Kaynak: eğitim modunun biriktirdiği gerçek dikteler (user_corrections/pending).
Uzunluk gruplarına göre dengeli, zamana yayılmış, tekrar metinler elenmiş
~150 kayıt seçer; sesleri ml/eval/audio/'ya kopyalar, clips.jsonl yazar.

Seçilen kayıtlar EĞİTİMDEN AYRI TUTULUR (ses eğitimi yapılırsa
clips.jsonl'deki dosyalar dışlanmalı — yoksa ölçüm kendini kandırır).

Kullanım: cd backend && PYTHONPATH=src .venv/bin/python ../ml/eval/select_clips.py
"""
import json
import re
import shutil
from pathlib import Path

import numpy as np
import soundfile as sf

from voiceflow.transcription.whisper import WhisperConfig, WhisperTranscriber

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "ml/whisper/datasets/user_corrections/pending"
OUT = ROOT / "ml/eval"
AUDIO = OUT / "audio"

# (ad, min sn, max sn, adet) — uzun kayıtlar düzeltmesi yorucu, az tutuldu
BUCKETS = [("<4s", 0.5, 4, 40), ("4-10s", 4, 10, 45), ("10-30s", 10, 30, 45), ("30-60s", 30, 60, 20)]
MIN_RMS = 0.0003  # backend'in sessiz kayıt eşiğiyle aynı


def _norm(text: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", text.lower()).split())


def main() -> None:
    AUDIO.mkdir(parents=True, exist_ok=True)
    candidates: dict[str, list[tuple[Path, float]]] = {b[0]: [] for b in BUCKETS}
    for f in sorted(SRC.glob("*.wav")):  # dosya adı = ms zaman damgası → kronolojik
        dur = sf.info(f).duration
        bucket = next((b for b in BUCKETS if b[1] <= dur < b[2]), None)
        if bucket is None:
            continue
        audio, _ = sf.read(f, dtype="float32")
        if float(np.sqrt(np.mean(audio ** 2))) < MIN_RMS:
            continue
        candidates[bucket[0]].append((f, dur))

    transcriber = WhisperTranscriber(config=WhisperConfig())
    clips, seen = [], set()
    for name, _, _, want in BUCKETS:
        pool = candidates[name]
        # Zamana eşit yay; tekrar metin çıkarsa sıradaki adaya geç
        step = max(1, len(pool) // (want * 2))
        picked = 0
        for f, dur in pool[::step] + pool:
            if picked == want:
                break
            if f.name in {c["file"] for c in clips}:
                continue
            audio, _ = sf.read(f, dtype="float32")
            prefill = transcriber.transcribe(audio).text.strip()
            key = _norm(prefill)
            if not key or key in seen:
                continue
            seen.add(key)
            shutil.copy2(f, AUDIO / f.name)
            clips.append({"id": f.stem, "file": f.name, "duration": round(dur, 2),
                          "bucket": name, "prefill": prefill})
            picked += 1
        print(f"{name}: {picked}/{want} (aday {len(pool)})", flush=True)

    with (OUT / "clips.jsonl").open("w", encoding="utf-8") as fh:
        for c in clips:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    total = sum(c["duration"] for c in clips)
    print(f"{len(clips)} kayıt, toplam {total / 60:.0f} dk ses → {OUT / 'clips.jsonl'}")


if __name__ == "__main__":
    main()
