"""punctuate_issai.py — ISSAI transkript metinlerine noktalama/büyük harf/Türkçe karakter ekler.

Girdi : ml/whisper/datasets/issai/issai_pairs_clean.jsonl  (input alanı)
Çıktı : ml/whisper/datasets/issai/issai_punctuated.jsonl   (original + punctuated)

Kullanım:
    export ANTHROPIC_API_KEY=sk-ant-...
    python ml/whisper/scripts/punctuate_issai.py
    python ml/whisper/scripts/punctuate_issai.py --workers 30 --model claude-haiku-4-5-20251001
    python ml/whisper/scripts/punctuate_issai.py --dry-run 20   # ilk 20 satırı test et

Resume: Script kesilirse kaldığı yerden devam eder (checkpoint dosyası saklar).
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

import anthropic

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_ROOT   = Path(__file__).parents[3]
INPUT_FILE  = REPO_ROOT / "ml/whisper/datasets/issai/issai_pairs_clean.jsonl"
OUTPUT_FILE = REPO_ROOT / "ml/whisper/datasets/issai/issai_punctuated.jsonl"
CKPT_FILE   = REPO_ROOT / "ml/whisper/datasets/issai/.punctuate_checkpoint.json"

# ── Prompt ────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = (
    "Sen bir Türkçe metin düzeltme asistanısın. "
    "Verilen metne SADECE şunları ekle/düzelt:\n"
    "- Cümle başı büyük harf\n"
    "- Virgül, nokta, soru işareti gibi noktalama işaretleri\n"
    "- Doğru Türkçe karakterler (ş, ğ, ı, ü, ö, ç)\n\n"
    "YAPMA: Kelime ekleme, çıkarma, anlam değiştirme.\n"
    "Sadece düzeltilmiş metni ver, açıklama yapma."
)


def build_prompt(text: str) -> str:
    return f"Metin: {text}"


# ── Checkpoint ────────────────────────────────────────────────────────────────
def load_checkpoint() -> set[int]:
    """Daha önce işlenen satır indexlerini döndür."""
    if CKPT_FILE.exists():
        data = json.loads(CKPT_FILE.read_text())
        return set(data.get("done", []))
    return set()


def save_checkpoint(done: set[int]) -> None:
    CKPT_FILE.write_text(json.dumps({"done": sorted(done)}))


# ── API call ──────────────────────────────────────────────────────────────────
async def punctuate_one(
    client: anthropic.AsyncAnthropic,
    model: str,
    idx: int,
    original: str,
    semaphore: asyncio.Semaphore,
    retries: int = 3,
) -> tuple[int, str, str]:
    """Tek bir metni API ile düzelt. (idx, original, punctuated) döndür."""
    async with semaphore:
        for attempt in range(retries):
            try:
                msg = await client.messages.create(
                    model=model,
                    max_tokens=256,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": build_prompt(original)}],
                )
                punctuated = msg.content[0].text.strip()
                return idx, original, punctuated
            except anthropic.RateLimitError:
                wait = 2 ** attempt
                print(f"  [rate limit] idx={idx}, {wait}s bekleniyor...")
                await asyncio.sleep(wait)
            except Exception as e:
                if attempt == retries - 1:
                    print(f"  [hata] idx={idx}: {e}")
                    return idx, original, original  # hata → orijinali koru
                await asyncio.sleep(1)
    return idx, original, original


# ── Main ──────────────────────────────────────────────────────────────────────
async def run(args: argparse.Namespace) -> None:
    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
    if not api_key:
        # .env dosyasından oku
        env_file = REPO_ROOT / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("ANTHROPIC_API_KEY=") or line.startswith("CLAUDE_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not api_key:
        print("HATA: ANTHROPIC_API_KEY bulunamadı.")
        sys.exit(1)

    # Girdi oku
    lines = INPUT_FILE.read_text(encoding="utf-8").splitlines()
    total = len(lines)
    print(f"Toplam satır: {total}")

    if args.dry_run:
        lines = lines[: args.dry_run]
        print(f"Dry-run: ilk {args.dry_run} satır işlenecek")

    # Checkpoint — daha önce işlenenler
    done_set = load_checkpoint() if not args.dry_run else set()
    print(f"Zaten işlendi: {len(done_set)}")

    # Çıktı dosyası — append mode (resume destekli)
    out_mode = "a" if done_set and not args.dry_run else "w"
    out_file = open(OUTPUT_FILE if not args.dry_run else "/dev/null", out_mode, encoding="utf-8")

    client = anthropic.AsyncAnthropic(api_key=api_key)
    semaphore = asyncio.Semaphore(args.workers)

    # Görevleri oluştur
    tasks = []
    for idx, raw in enumerate(lines):
        if idx in done_set:
            continue
        try:
            obj = json.loads(raw)
            original = obj.get("input", "").strip()
        except json.JSONDecodeError:
            continue
        if not original:
            continue
        tasks.append(
            punctuate_one(client, args.model, idx, original, semaphore)
        )

    print(f"İşlenecek: {len(tasks)} satır | Workers: {args.workers} | Model: {args.model}")

    start = time.time()
    processed = 0
    ckpt_batch: set[int] = set()

    # Batch olarak çalıştır — tüm görevler async, semaphore ile sınırlandırılmış
    for coro in asyncio.as_completed(tasks):
        idx, original, punctuated = await coro
        processed += 1
        ckpt_batch.add(idx)

        if not args.dry_run:
            out_file.write(json.dumps({"original": original, "punctuated": punctuated}, ensure_ascii=False) + "\n")
        else:
            print(f"  [{idx}] {original[:60]}")
            print(f"       → {punctuated[:60]}")

        # Checkpoint her 500 satırda
        if len(ckpt_batch) >= 500 and not args.dry_run:
            done_set.update(ckpt_batch)
            save_checkpoint(done_set)
            ckpt_batch.clear()
            elapsed = time.time() - start
            rate = processed / elapsed
            remaining = (len(tasks) - processed) / rate if rate > 0 else 0
            print(
                f"  ✓ {processed}/{len(tasks)} | "
                f"{rate:.1f} satır/sn | "
                f"~{remaining/60:.0f} dk kaldı"
            )

    # Son checkpoint
    if ckpt_batch and not args.dry_run:
        done_set.update(ckpt_batch)
        save_checkpoint(done_set)

    out_file.close()

    elapsed = time.time() - start
    print(f"\nTamamlandı: {processed} satır, {elapsed/60:.1f} dakika")
    if not args.dry_run:
        print(f"Çıktı: {OUTPUT_FILE}")


def main() -> None:
    parser = argparse.ArgumentParser(description="ISSAI transkriptlerini noktalama ile düzelt")
    parser.add_argument("--workers",  type=int,  default=20,
                        help="Paralel API çağrısı sayısı (default: 20)")
    parser.add_argument("--model",    type=str,  default="claude-haiku-4-5-20251001",
                        help="Claude model ID")
    parser.add_argument("--dry-run",  type=int,  default=0, metavar="N",
                        help="İlk N satırı test et, dosyaya yazma")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
