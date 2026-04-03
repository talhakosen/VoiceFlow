"""word_order_generator.py — Türkçe kelime sırası düzeltme pair'leri üret.

Whisper bazen kelimeleri yanlış sırayla yazabilir (özellikle SOV yapısı bozulur).
Bu script Claude ile gerçekçi (bozuk sıra → doğru sıra) pair'leri üretir.

Çıktı (JSONL):
  {"input": "...", "output": "...", "category": "word_order"}

Kullanım:
  python word_order_generator.py --output data_gen/word_order_pairs.jsonl --target 500
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
    print("ERROR: pip install anthropic", file=sys.stderr)
    sys.exit(1)


MODEL = "claude-opus-4-6"

_SYSTEM_PROMPT = """\
Sen bir Türkçe ASR veri üreticisisin. Türkçe SOV (Özne-Nesne-Yüklem) cümle yapısını ihlal eden,
kelime sırası bozulmuş Whisper çıktıları ve bunların doğru halleri olan pair'ler üret.

- input: Whisper'ın yanlış sırayla yazdığı ham metin.
  * Kelime sırası bozuk (yüklem cümle ortasında, nesne başta, özne sonda, vb.)
  * Türkçe karakter hataları da olabilir (ç→c, ş→s vb.)
  * Büyük harf / noktalama eksik olabilir
  * Doğal konuşma dili — kısa cümleler (5-15 kelime)

- output: Doğru kelime sırası ve Türkçe karakterlerle düzeltilmiş metin.
  * Hiçbir kelime eklenmez veya çıkarılmaz — sadece sıra ve karakter düzeltilir
  * Büyük harf ve noktalama eklenir

Örnek:
  input:  "kuruyorum ben bugün bir rapor"
  output: "Ben bugün bir rapor kuruyorum."

  input:  "gitti markete annem dun"
  output: "Annem dün markete gitti."

  input:  "yapacagiz toplantida bunu konusmayi"
  output: "Bunu toplantıda konuşacağız."

HER ZAMAN SADECE JSON array döndür:
[
  {"input": "...", "output": "...", "category": "word_order"},
  ...
]"""

_USER_PROMPT = "Kelime sırası bozuk {n} adet Türkçe pair üret. Çeşitli konular: iş, günlük hayat, teknik, sosyal. JSON array döndür."


def _call_claude(client, batch_size: int, retries: int = 3) -> list[dict]:
    for attempt in range(1, retries + 1):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": _USER_PROMPT.format(n=batch_size)}],
            )
            raw = response.content[0].text.strip()

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
                    and "input" in p and "output" in p
                    and isinstance(p["input"], str) and isinstance(p["output"], str)
                    and p["input"].strip() and p["output"].strip()
                    and p["input"].strip() != p["output"].strip()
                ):
                    validated.append({
                        "input": p["input"].strip(),
                        "output": p["output"].strip(),
                        "category": "word_order",
                    })
            return validated

        except (json.JSONDecodeError, ValueError) as e:
            print(f"  [attempt {attempt}/{retries}] Parse error: {e}", file=sys.stderr)
            if attempt < retries:
                time.sleep(2 ** attempt)
        except Exception as e:
            print(f"  [attempt {attempt}/{retries}] API error: {e}", file=sys.stderr)
            if attempt < retries:
                time.sleep(2 ** attempt)
    return []


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data_gen/word_order_pairs.jsonl"))
    parser.add_argument("--target", type=int, default=500)
    parser.add_argument("--batch-size", type=int, default=15)
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--api-key", type=str, default=None)
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY gerekli", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    collected: list[dict] = []

    print(f"Hedef: {args.target} pair", file=sys.stderr)

    while len(collected) < args.target:
        remaining = args.target - len(collected)
        batch = min(args.batch_size, remaining)
        pairs = _call_claude(client, batch)

        if pairs:
            collected.extend(pairs[:remaining])
            print(f"  {len(collected)}/{args.target}", file=sys.stderr, end="\r")
        else:
            print("  WARNING: boş batch, tekrar deneniyor...", file=sys.stderr)

        if len(collected) < args.target:
            time.sleep(args.delay)

    random.shuffle(collected)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        for p in collected:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    print(f"\n{len(collected)} pair → {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
