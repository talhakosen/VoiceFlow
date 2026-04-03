"""claude_generator.py — Generate natural Turkish ASR correction pairs via Claude API.

Uses claude-haiku-4-5-20251001 (cost-efficient) to produce ~1000 realistic
Turkish speech-recognition (input, output) pairs across three domains:
  - engineering  : code reviews, PR descriptions, technical discussions
  - office       : emails, meeting notes, business correspondence
  - general      : everyday conversations, personal dictation

Output format (JSONL):
  {"input": "<raw_asr_like>", "output": "<corrected>", "category": "engineering|office|general"}

Usage:
  ANTHROPIC_API_KEY=sk-... python claude_generator.py \
      --output data_gen/claude_pairs.jsonl \
      --target 1000 \
      --batch-size 10
"""

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("ERROR: anthropic package not installed. Run: pip install anthropic", file=sys.stderr)
    sys.exit(1)


MODEL = "claude-haiku-4-5-20251001"

# ---------------------------------------------------------------------------
# Prompts per category
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
Sen bir Türkçe ASR (otomatik konuşma tanıma) veri üreticisisin.
Her seferinde senden belirtilen kategoride (input, output) çiftleri isteyeceğim.

- input: Bir kullanıcının sesli dikte ettiği ham metin. Whisper ASR çıktısı gibi görünmeli:
  * Türkçe karakter hataları olabilir (ç→c, ş→s, ğ→g, ı→i, ö→o, ü→u)
  * Büyük harf eksikliği olabilir
  * Noktalama işareti olmayabilir
  * Filler kelimeler olabilir (yani, şey, hani, ee, aa)
  * Bazen geri dönüş/düzeltme olabilir ("hayır yok yok", "scratch that")
  * Bazen sözel noktalama (virgül, nokta, soru işareti)

- output: Düzeltilmiş, doğal Türkçe metin.
  * Türkçe karakterler doğru
  * Büyük harf ve noktalama doğru
  * Filler kelimeler temizlenmiş
  * Geri dönüş işlenmiş, son niyet muhafaza edilmiş

HER ZAMAN SADECE JSON array döndür, başka hiçbir şey yazma:
[
  {"input": "...", "output": "...", "category": "<kategori>"},
  ...
]"""

_USER_PROMPTS = {
    "engineering": """\
Yazılım mühendisliği kategorisinde {n} çift üret.
Konular: kod review, pull request açıklamaları, bug raporu, teknik tartışma,
         mimari karar, deployment adımları, hata mesajları açıklama.
Teknik terimler (AppViewModel, async/await, Docker, Git, API endpoint, vb.) yer alabilir.
category değeri: "engineering"
JSON array döndür.""",

    "office": """\
Kurumsal ofis iletişimi kategorisinde {n} çift üret.
Konular: email yazma, toplantı notu, bütçe raporu, müşteri görüşmesi,
         proje güncelleme, insan kaynakları, tedarik zinciri.
Resmi iş Türkçesi kullan.
category değeri: "office"
JSON array döndür.""",

    "general": """\
Günlük konuşma kategorisinde {n} çift üret.
Konular: alışveriş, hava durumu, sosyal planlar, kişisel günlük,
         seyahat, yemek, aile, hobi.
Doğal konuşma dili kullan.
category değeri: "general"
JSON array döndür.""",
}


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

def _call_claude(
    client: "anthropic.Anthropic",
    category: str,
    batch_size: int,
    retries: int = 3,
) -> list[dict]:
    """Call Claude API and return a list of pair dicts."""
    user_msg = _USER_PROMPTS[category].format(n=batch_size)

    for attempt in range(1, retries + 1):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )
            raw = response.content[0].text.strip()

            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```", 2)[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()
            if raw.endswith("```"):
                raw = raw[:-3].strip()

            pairs = json.loads(raw)
            if not isinstance(pairs, list):
                raise ValueError("Expected JSON array")

            validated = []
            for p in pairs:
                if (
                    isinstance(p, dict)
                    and "input" in p
                    and "output" in p
                    and isinstance(p["input"], str)
                    and isinstance(p["output"], str)
                    and p["input"].strip()
                    and p["output"].strip()
                ):
                    validated.append({
                        "input": p["input"].strip(),
                        "output": p["output"].strip(),
                        "category": p.get("category", category),
                    })
            return validated

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(
                f"  [attempt {attempt}/{retries}] Parse error for {category}: {e}",
                file=sys.stderr,
            )
            if attempt < retries:
                time.sleep(2 ** attempt)
        except Exception as e:
            print(
                f"  [attempt {attempt}/{retries}] API error for {category}: {e}",
                file=sys.stderr,
            )
            if attempt < retries:
                time.sleep(2 ** attempt)

    return []


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate natural Turkish ASR correction pairs using Claude API.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data_gen/claude_pairs.jsonl"),
        help="Output JSONL file path.",
    )
    parser.add_argument(
        "--target",
        type=int,
        default=1000,
        help="Total number of pairs to generate.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Pairs per API call (higher = fewer calls but larger prompts).",
    )
    parser.add_argument(
        "--categories",
        nargs="+",
        default=["engineering", "office", "general"],
        choices=["engineering", "office", "general"],
        help="Categories to generate.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Seconds to wait between API calls (rate limiting).",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Anthropic API key (default: ANTHROPIC_API_KEY env var).",
    )
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(
            "ERROR: Set ANTHROPIC_API_KEY environment variable or use --api-key.",
            file=sys.stderr,
        )
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    # Distribute target evenly across categories
    per_category = args.target // len(args.categories)
    remainder = args.target % len(args.categories)

    category_targets = {cat: per_category for cat in args.categories}
    for i, cat in enumerate(args.categories):
        if i < remainder:
            category_targets[cat] += 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    total_written = 0
    all_pairs: list[dict] = []

    for category in args.categories:
        target = category_targets[category]
        collected: list[dict] = []
        print(
            f"Generating {target} pairs for category '{category}'...",
            file=sys.stderr,
        )

        while len(collected) < target:
            remaining = target - len(collected)
            batch = min(args.batch_size, remaining)
            pairs = _call_claude(client, category, batch)

            if pairs:
                collected.extend(pairs[:remaining])
                print(
                    f"  {len(collected)}/{target} collected",
                    file=sys.stderr,
                    end="\r",
                )
            else:
                print(f"  WARNING: Empty batch for {category}, retrying...", file=sys.stderr)

            if len(collected) < target:
                time.sleep(args.delay)

        print(f"  Done: {len(collected)} pairs", file=sys.stderr)
        all_pairs.extend(collected)
        total_written += len(collected)

    # Shuffle and write
    random.shuffle(all_pairs)
    with open(args.output, "w", encoding="utf-8") as f:
        for pair in all_pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    print(f"\nWritten {total_written} pairs to {args.output}", file=sys.stderr)
    counts: dict[str, int] = {}
    for p in all_pairs:
        counts[p["category"]] = counts.get(p["category"], 0) + 1
    for cat, n in sorted(counts.items()):
        print(f"  {cat}: {n}", file=sys.stderr)


if __name__ == "__main__":
    main()
