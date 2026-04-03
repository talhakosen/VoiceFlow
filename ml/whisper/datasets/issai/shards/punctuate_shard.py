"""punctuate_shard.py — Tek bir ISSAI shard dosyasına noktalama/Türkçe karakter ekler.

Kullanım:
    export ANTHROPIC_API_KEY=sk-ant-...
    python punctuate_shard.py shard_005.jsonl
    python punctuate_shard.py shard_005.jsonl --workers 20 --model claude-haiku-4-5-20251001

Girdi : {"input": "Turkish text"}
Çıktı : {"original": "...", "punctuated": "..."}

Resume: Kesilirse kaldığı yerden devam eder.
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

import anthropic

SYSTEM_PROMPT = (
    "Sen bir Türkçe metin düzeltme asistanısın. "
    "Verilen metne SADECE şunları ekle/düzelt: "
    "virgül, nokta, soru işareti gibi noktalama işaretleri; "
    "doğru Türkçe karakterler (ş, ğ, ı, ü, ö, ç); "
    "özel isim büyük harfleri. "
    "YAPMA: Kelime ekleme, çıkarma, anlam değiştirme. "
    "Sadece düzeltilmiş metni ver."
)


def get_api_key() -> str:
    key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
    if key:
        return key
    env_path = Path(__file__).parents[5] / ".env"
    if not env_path.exists():
        env_path = Path("/Users/talhakosen/Developer/utils/voiceflow/.env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("ANTHROPIC_API_KEY=") or line.startswith("CLAUDE_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    print("HATA: ANTHROPIC_API_KEY bulunamadı.")
    sys.exit(1)


async def punctuate_one(
    client: anthropic.AsyncAnthropic,
    model: str,
    idx: int,
    original: str,
    semaphore: asyncio.Semaphore,
    retries: int = 3,
) -> tuple[int, str, str]:
    async with semaphore:
        for attempt in range(retries):
            try:
                msg = await client.messages.create(
                    model=model,
                    max_tokens=512,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": f"Metin: {original}"}],
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
                    return idx, original, original
                await asyncio.sleep(1)
    return idx, original, original


async def run(args: argparse.Namespace) -> None:
    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = Path(__file__).parent / args.input

    stem = input_path.stem
    output_path = input_path.parent / f"{stem}_punctuated.jsonl"
    ckpt_path = input_path.parent / f".{stem}_ckpt.json"

    if not input_path.exists():
        print(f"HATA: {input_path} bulunamadı.")
        sys.exit(1)

    lines = input_path.read_text(encoding="utf-8").splitlines()
    total = len(lines)
    print(f"Girdi: {input_path}")
    print(f"Çıktı: {output_path}")
    print(f"Toplam satır: {total}")

    # Checkpoint — resume support
    done_set: set[int] = set()
    if ckpt_path.exists() and not args.reset:
        data = json.loads(ckpt_path.read_text())
        done_set = set(data.get("done", []))
        print(f"Zaten işlendi: {len(done_set)}")

    api_key = get_api_key()
    client = anthropic.AsyncAnthropic(api_key=api_key)
    semaphore = asyncio.Semaphore(args.workers)

    # Build tasks
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
        tasks.append(punctuate_one(client, args.model, idx, original, semaphore))

    print(f"İşlenecek: {len(tasks)} satır | Workers: {args.workers} | Model: {args.model}")

    out_mode = "a" if done_set else "w"
    out_file = open(output_path, out_mode, encoding="utf-8")

    start = time.time()
    processed = 0
    pending_ckpt: set[int] = set()

    for coro in asyncio.as_completed(tasks):
        idx, original, punctuated = await coro
        processed += 1
        pending_ckpt.add(idx)
        out_file.write(json.dumps({"original": original, "punctuated": punctuated}, ensure_ascii=False) + "\n")
        out_file.flush()

        if len(pending_ckpt) >= 200:
            done_set.update(pending_ckpt)
            ckpt_path.write_text(json.dumps({"done": sorted(done_set)}))
            pending_ckpt.clear()
            elapsed = time.time() - start
            rate = processed / elapsed
            remaining = (len(tasks) - processed) / rate if rate > 0 else 0
            print(f"  {processed}/{len(tasks)} | {rate:.1f} satır/sn | ~{remaining/60:.1f} dk kaldı")

    if pending_ckpt:
        done_set.update(pending_ckpt)
        ckpt_path.write_text(json.dumps({"done": sorted(done_set)}))

    out_file.close()
    elapsed = time.time() - start
    print(f"\nTamamlandı: {processed} satır, {elapsed/60:.1f} dakika")
    print(f"Çıktı: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="ISSAI shard dosyasını noktalama ile düzelt")
    parser.add_argument("input", nargs="?", default="shard_005.jsonl", help="Girdi JSONL dosyası")
    parser.add_argument("--workers", type=int, default=20, help="Paralel API çağrısı (default: 20)")
    parser.add_argument("--model", type=str, default="claude-haiku-4-5-20251001", help="Claude model ID")
    parser.add_argument("--reset", action="store_true", help="Checkpoint'i sıfırla, baştan başla")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
