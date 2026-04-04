#!/usr/bin/env python3
"""
Punctuate Turkish ground truth texts in a shard JSONL file using Claude Haiku.

Usage:
    ANTHROPIC_API_KEY=sk-ant-... python punctuate_shard.py <input_shard.jsonl> [output_shard.jsonl]

API key is read from ANTHROPIC_API_KEY env var or from the project .env file.
Output defaults to <input_stem>_punctuated.jsonl in same directory.

Rate limit: targets 45 req/min (1 request every ~1.33s) using a token-bucket pacer.
With 2000 lines this takes ~45 minutes. Use with a paid-tier key for faster throughput.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

import anthropic

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MODEL = "claude-haiku-4-5-20251001"
CONCURRENCY = 5             # concurrent in-flight requests
RATE_LIMIT_PER_MIN = 45     # stay safely below 50 req/min limit
MIN_INTERVAL = 60.0 / RATE_LIMIT_PER_MIN   # ~1.33s between request dispatches
MAX_RETRIES = 5
ENV_FILE = Path("/Users/talhakosen/Developer/utils/voiceflow/.env")

SYSTEM_PROMPT = (
    "Sen bir Türkçe metin düzeltme asistanısın. Verilen metne SADECE şunları ekle/düzelt: "
    "virgül, nokta, soru işareti gibi noktalama işaretleri; "
    "doğru Türkçe karakterler (ş, ğ, ı, ü, ö, ç); "
    "özel isim büyük harfleri. "
    "YAPMA: Kelime ekleme, çıkarma, anlam değiştirme. "
    "Sadece düzeltilmiş metni ver."
)


# ---------------------------------------------------------------------------
# API key resolution
# ---------------------------------------------------------------------------
def load_api_key() -> str | None:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key:
        return key
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line.startswith("ANTHROPIC_API_KEY="):
                key = line.split("=", 1)[1].strip()
                if key:
                    return key
    return None


# ---------------------------------------------------------------------------
# Token-bucket rate limiter
# ---------------------------------------------------------------------------
class RateLimiter:
    """Allows at most `rate_per_min` requests per minute using a token bucket."""

    def __init__(self, rate_per_min: float) -> None:
        self._interval = 60.0 / rate_per_min
        self._lock = asyncio.Lock()
        self._last_release = 0.0

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            wait = self._interval - (now - self._last_release)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_release = time.monotonic()


# ---------------------------------------------------------------------------
# Per-line processing
# ---------------------------------------------------------------------------
async def punctuate_text(
    client: anthropic.AsyncAnthropic,
    semaphore: asyncio.Semaphore,
    rate_limiter: RateLimiter,
    original: str,
    index: int,
) -> dict:
    async with semaphore:
        for attempt in range(MAX_RETRIES):
            await rate_limiter.acquire()
            try:
                response = await client.messages.create(
                    model=MODEL,
                    max_tokens=512,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": original}],
                )
                return {"original": original, "punctuated": response.content[0].text.strip()}
            except anthropic.RateLimitError:
                # Back off and retry — rate limiter will pace subsequent calls
                wait = 30 * (attempt + 1)
                print(
                    f"  [line {index}] rate limit (attempt {attempt + 1}/{MAX_RETRIES}), backing off {wait}s",
                    file=sys.stderr,
                )
                await asyncio.sleep(wait)
            except anthropic.APIStatusError as e:
                print(f"  [line {index}] API {e.status_code}: {e.message[:60]}", file=sys.stderr)
                if e.status_code >= 500:
                    await asyncio.sleep(10)
                else:
                    break
            except Exception as exc:
                print(f"  [line {index}] ERROR: {exc}", file=sys.stderr)
                break

    return {"original": original, "punctuated": original}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main(input_path: Path, output_path: Path) -> None:
    api_key = load_api_key()
    client = anthropic.AsyncAnthropic(api_key=api_key) if api_key else anthropic.AsyncAnthropic()

    semaphore = asyncio.Semaphore(CONCURRENCY)
    rate_limiter = RateLimiter(RATE_LIMIT_PER_MIN)

    lines = []
    with input_path.open(encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
                lines.append(obj.get("input", ""))
            except json.JSONDecodeError as e:
                print(f"  Skipping bad JSON line: {e}", file=sys.stderr)

    total = len(lines)
    eta_min = total / RATE_LIMIT_PER_MIN
    print(f"Processing {total} lines from {input_path.name}")
    print(f"  Rate limit: {RATE_LIMIT_PER_MIN} req/min  |  ETA: ~{eta_min:.0f} min")
    t0 = time.time()

    tasks = [
        punctuate_text(client, semaphore, rate_limiter, text, i)
        for i, text in enumerate(lines)
    ]
    results = await asyncio.gather(*tasks)

    elapsed = time.time() - t0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    changed = 0
    with output_path.open("w", encoding="utf-8") as out:
        for r in results:
            out.write(json.dumps(r, ensure_ascii=False) + "\n")
            if r["original"] != r["punctuated"]:
                changed += 1

    print(f"\nDone in {elapsed:.1f}s  ({elapsed/60:.1f} min)")
    print(f"  Total lines  : {total}")
    print(f"  Changed      : {changed}")
    print(f"  Unchanged    : {total - changed}")
    print(f"  Output       : {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python punctuate_shard.py <input.jsonl> [output.jsonl]", file=sys.stderr)
        sys.exit(1)

    input_path = Path(sys.argv[1]).resolve()
    if not input_path.exists():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    output_path = (
        Path(sys.argv[2]).resolve()
        if len(sys.argv) >= 3
        else input_path.parent / (input_path.stem + "_punctuated.jsonl")
    )

    asyncio.run(main(input_path, output_path))
