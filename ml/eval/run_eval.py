"""Dikte eval — etiketli kayıtları gerçek pipeline'dan geçir, hata oranını ölç.

İki metrik:
  asr      Whisper ham çıktısı vs söylenen (kelimesi kelimesine)
  content  pipeline çıktısı (sözlük + dolgu temizleme) vs söylenen, dolgular
           İKİ taraftan da atılmış — temizleyici işini yaptı diye ceza yemesin
Noktalama, büyük/küçük harf ve Türkçe karakter farkı (ş/s, ı/i…) yok sayılır —
etiketler bazen ASCII yazıldı ("dogru"), bunu hata saymamalı.

Her çalıştırma ml/eval/reports/'a yazılır ve bir öncekiyle karşılaştırılır.
Model/pencere/sözlük/prompt değişikliğinden ÖNCE ve SONRA çalıştır.

Kullanım: cd backend && PYTHONPATH=src .venv/bin/python ../ml/eval/run_eval.py [--label isim]
"""
import argparse
import asyncio
import json
import re
import sqlite3
import time
from pathlib import Path

import jiwer
import soundfile as sf

from voiceflow.core.config import DB_PATH
from voiceflow.db import get_dictionary
from voiceflow.services.dictionary import _apply_aho_corasick, _build_automaton
from voiceflow.services.filler_cleaner import clean_fillers
from voiceflow.transcription.whisper import WhisperConfig, WhisperTranscriber

HERE = Path(__file__).resolve().parent
# Normalizasyondan SONRA eşleşir → ASCII biçimler
FILLERS = re.compile(r"^(sey|yani|hani|e+|a+|i+|hmm+|imm+)$")
_FOLD = str.maketrans("çğıöşüâîû", "cgiosuaiu")


def normalize(text: str) -> list[str]:
    """Türkçe küçük harf, noktalamasız, Türkçe karakterleri sadeleştirilmiş kelimeler."""
    text = text.replace("İ", "i").replace("I", "ı").lower().replace("'", "")
    return re.sub(r"[^\w\s]", " ", text).translate(_FOLD).split()


def content(words: list[str]) -> list[str]:
    return [w for w in words if not FILLERS.match(w)]


def wer(ref: list[str], hyp: list[str]) -> float:
    if not ref:
        return 0.0 if not hyp else 1.0
    return jiwer.wer(" ".join(ref), " ".join(hyp) or "∅")


def last_user_id() -> str | None:
    row = sqlite3.connect(DB_PATH).execute(
        "SELECT user_id FROM transcriptions WHERE user_id != '' ORDER BY id DESC LIMIT 1").fetchone()
    return row[0] if row else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="", help="rapora not (ör. 'pencere-fix')")
    ap.add_argument("--refs", default=str(HERE / "references.jsonl"))
    ap.add_argument("--model", default="", help="Whisper modeli (boş = config.yaml'daki)")
    args = ap.parse_args()

    clips = {c["id"]: c for c in map(json.loads, (HERE / "clips.jsonl").read_text().splitlines())}
    refs = [r for r in map(json.loads, Path(args.refs).read_text().splitlines()) if r["status"] == "ok"]
    if not refs:
        raise SystemExit("Etiketli kayıt yok — önce label_server.py ile doğru metinleri yaz.")

    user_id = last_user_id()
    entries = asyncio.run(get_dictionary(user_id=user_id, include_smart=True)) if user_id else []
    automaton = _build_automaton(entries) if entries else None
    transcriber = WhisperTranscriber(
        config=WhisperConfig(model_name=args.model) if args.model else WhisperConfig())

    rows = []
    t0 = time.perf_counter()
    for r in refs:
        c = clips[r["id"]]
        audio, _ = sf.read(HERE / "audio" / c["file"], dtype="float32")
        raw = transcriber.transcribe(audio).text.strip()
        out = raw
        if automaton is not None:
            out = _apply_aho_corasick(_apply_aho_corasick(out, automaton), automaton)
        out = clean_fillers(out)
        ref_w = normalize(r["reference"])
        rows.append({
            "id": c["id"], "bucket": c["bucket"], "duration": c["duration"],
            "reference": r["reference"], "raw": raw, "final": out,
            "asr": wer(ref_w, normalize(raw)),
            "content": wer(content(ref_w), content(normalize(out))),
        })
    elapsed = time.perf_counter() - t0

    def corpus(metric: str, sel: list[dict]) -> float:
        # Kelime sayısına göre ağırlıklı — kısa kayıtlar ortalamayı domine etmesin
        refs_ = [" ".join(normalize(x["reference"]) if metric == "asr" else content(normalize(x["reference"])))
                 for x in sel]
        hyps_ = [" ".join(normalize(x["raw"]) if metric == "asr" else content(normalize(x["final"]))) or "∅"
                 for x in sel]
        pairs = [(a, b) for a, b in zip(refs_, hyps_) if a]
        return jiwer.wer([a for a, _ in pairs], [b for _, b in pairs]) if pairs else 0.0

    order = list(dict.fromkeys(c["bucket"] for c in clips.values()))  # select_clips sırası: kısadan uzuna
    buckets = [b for b in order if any(x["bucket"] == b for x in rows)]
    summary = {
        "label": args.label, "model": transcriber.config.model_name,
        "n": len(rows), "seconds": round(elapsed, 1),
        "asr": corpus("asr", rows), "content": corpus("content", rows),
        "by_bucket": {b: {"n": sum(x["bucket"] == b for x in rows),
                          "asr": corpus("asr", [x for x in rows if x["bucket"] == b]),
                          "content": corpus("content", [x for x in rows if x["bucket"] == b])}
                      for b in buckets},
    }

    print(f"\n{len(rows)} kayıt · {elapsed:.0f} sn")
    print(f"{'':10} {'ASR':>7} {'İÇERİK':>8}")
    print(f"{'TOPLAM':10} {summary['asr']:7.1%} {summary['content']:8.1%}")
    for b, s in summary["by_bucket"].items():
        print(f"{b:10} {s['asr']:7.1%} {s['content']:8.1%}   (n={s['n']})")

    print("\nEn kötü 10 (içerik):")
    for x in sorted(rows, key=lambda x: -x["content"])[:10]:
        print(f"  %{x['content'] * 100:3.0f}  SÖYLENEN: {x['reference'][:90]}\n        ÇIKTI:    {x['final'][:90]}")

    reports = HERE / "reports"
    reports.mkdir(exist_ok=True)
    previous = sorted(reports.glob("*.json"))
    if previous:
        prev = json.loads(previous[-1].read_text())
        prev_rows = {x["id"]: x for x in prev["rows"]}
        better = sum(1 for x in rows if x["id"] in prev_rows and x["content"] < prev_rows[x["id"]]["content"] - 1e-9)
        worse = sum(1 for x in rows if x["id"] in prev_rows and x["content"] > prev_rows[x["id"]]["content"] + 1e-9)
        print(f"\nÖnceki rapora göre ({previous[-1].stem}): ASR {prev['summary']['asr']:.1%} → {summary['asr']:.1%}, "
              f"içerik {prev['summary']['content']:.1%} → {summary['content']:.1%} · "
              f"{better} kayıt iyileşti, {worse} kötüleşti")

    out_path = reports / f"{time.strftime('%Y%m%d-%H%M%S')}{'-' + args.label if args.label else ''}.json"
    out_path.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=1))
    print(f"\nRapor: {out_path.relative_to(HERE.parents[1])}")


if __name__ == "__main__":
    main()
