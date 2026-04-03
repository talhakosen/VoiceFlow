#!/usr/bin/env python3
"""
Punctuate Turkish ground truth texts in a shard JSONL file using Claude Haiku.

Default run (no args — processes shard_009):
    ANTHROPIC_API_KEY=sk-ant-... python punctuate_shard.py

With explicit paths:
    ANTHROPIC_API_KEY=sk-ant-... python punctuate_shard.py <input_shard.jsonl> [output_shard.jsonl]

If output is not specified, it defaults to <input_stem>_punctuated.jsonl in the same directory.
API key is read from ANTHROPIC_API_KEY env var or from the project .env file.
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
_HERE = Path(__file__).parent
DEFAULT_INPUT = _HERE / "shards" / "shard_009.jsonl"
DEFAULT_OUTPUT = _HERE / "shards" / "shard_009_punctuated.jsonl"

MODEL = "claude-haiku-4-5-20251001"
SEMAPHORE_LIMIT = 20
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
    """Return API key string, or None to let the SDK auto-discover it."""
    # 1. Environment variable
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key:
        return key

    # 2. .env file
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line.startswith("ANTHROPIC_API_KEY="):
                key = line.split("=", 1)[1].strip()
                if key:
                    return key

    # 3. Let the SDK discover via keychain / ANTHROPIC_API_KEY set by Claude Code
    return None


# ---------------------------------------------------------------------------
# Per-line processing
# ---------------------------------------------------------------------------
async def punctuate_text(
    client: anthropic.AsyncAnthropic,
    semaphore: asyncio.Semaphore,
    original: str,
    index: int,
) -> dict:
    async with semaphore:
        try:
            response = await client.messages.create(
                model=MODEL,
                max_tokens=512,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": original}],
            )
            punctuated = response.content[0].text.strip()
        except Exception as exc:
            print(f"  [line {index}] ERROR: {exc}", file=sys.stderr)
            punctuated = original  # fallback: keep original on error

    return {"original": original, "punctuated": punctuated}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main(input_path: Path, output_path: Path) -> None:
    api_key = load_api_key()
    client = anthropic.AsyncAnthropic(api_key=api_key) if api_key else anthropic.AsyncAnthropic()
    semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)

    # Read all lines
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
    print(f"Processing {total} lines from {input_path.name} ...")
    t0 = time.time()

    # Dispatch all tasks concurrently (semaphore controls in-flight count)
    tasks = [
        punctuate_text(client, semaphore, text, i)
        for i, text in enumerate(lines)
    ]

    results = await asyncio.gather(*tasks)

    elapsed = time.time() - t0

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    changed = 0
    with output_path.open("w", encoding="utf-8") as out:
        for r in results:
            out.write(json.dumps(r, ensure_ascii=False) + "\n")
            if r["original"] != r["punctuated"]:
                changed += 1

    print(f"\nDone in {elapsed:.1f}s")
    print(f"  Total lines  : {total}")
    print(f"  Changed      : {changed}")
    print(f"  Unchanged    : {total - changed}")
    print(f"  Output       : {output_path}")


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        input_path = Path(sys.argv[1]).resolve()
    else:
        input_path = DEFAULT_INPUT

    if not input_path.exists():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) >= 3:
        output_path = Path(sys.argv[2]).resolve()
    elif len(sys.argv) < 2:
        output_path = DEFAULT_OUTPUT
    else:
        output_path = input_path.parent / (input_path.stem + "_punctuated.jsonl")

    asyncio.run(main(input_path, output_path))
