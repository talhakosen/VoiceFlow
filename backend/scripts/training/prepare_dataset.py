"""prepare_dataset.py — Merge all data sources → train/valid/test JSONL.

Reads:
  - data_gen/corruption_pairs.jsonl  (3K synthetic corruption pairs)
  - data_gen/claude_pairs.jsonl      (1K Claude-generated pairs)
  - data_gen/whisper_pairs.jsonl     (500 real Whisper error pairs)

Applies Qwen2.5 chat template format and splits 80/10/10.

Output:
  training/train.jsonl
  training/valid.jsonl
  training/test.jsonl

Format per line:
  {
    "prompt":     "<|im_start|>user\\n{input}<|im_end|>\\n<|im_start|>assistant\\n",
    "completion": "{output}<|im_end|>"
  }

Usage:
  python prepare_dataset.py \
      --sources data_gen/corruption_pairs.jsonl data_gen/claude_pairs.jsonl \
                data_gen/whisper_pairs.jsonl \
      --output-dir training/ \
      --train-ratio 0.8 \
      --valid-ratio 0.1
"""

import argparse
import json
import random
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Chat template formatting (Qwen2.5 / ChatML)
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are a speech-to-text post-processor. Fix Turkish/English ASR output: "
    "correct Turkish characters (ç, ş, ğ, ı, ö, ü), add punctuation, "
    "remove filler words, handle backtracking. Output ONLY the corrected text."
)


def _format_pair(input_text: str, output_text: str) -> dict:
    """Format a single pair into mlx-lm text format (avoids double chat-template wrapping)."""
    text = (
        f"<|im_start|>system\n{_SYSTEM_PROMPT}<|im_end|>\n"
        f"<|im_start|>user\n{input_text}<|im_end|>\n"
        f"<|im_start|>assistant\n{output_text}<|im_end|>"
    )
    return {"text": text}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_jsonl(path: Path) -> list[dict]:
    """Load a JSONL file and return a list of dicts."""
    if not path.exists():
        print(f"WARNING: {path} not found, skipping.", file=sys.stderr)
        return []

    records = []
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                if "input" in record and "output" in record:
                    records.append(record)
                else:
                    print(
                        f"WARNING: {path}:{lineno} missing 'input'/'output', skipping.",
                        file=sys.stderr,
                    )
            except json.JSONDecodeError as e:
                print(f"WARNING: {path}:{lineno} JSON error: {e}", file=sys.stderr)

    return records


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Merge fine-tuning sources and split into train/valid/test.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        type=Path,
        default=[
            Path("data_gen/corruption_pairs.jsonl"),
            Path("data_gen/claude_pairs.jsonl"),
            Path("data_gen/whisper_pairs.jsonl"),
            Path("data_gen/word_order_pairs.jsonl"),
            Path("data_gen/gecturk_pairs.jsonl"),
        ],
        help="JSONL source files to merge.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("training/"),
        help="Directory where train/valid/test.jsonl will be written.",
    )
    parser.add_argument(
        "--train-ratio",
        type=float,
        default=0.8,
        help="Fraction of data for training set.",
    )
    parser.add_argument(
        "--valid-ratio",
        type=float,
        default=0.1,
        help="Fraction of data for validation set (remainder → test).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility.",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=None,
        help="Cap total samples (useful for quick experiments).",
    )
    args = parser.parse_args()

    test_ratio = 1.0 - args.train_ratio - args.valid_ratio
    if test_ratio < 0:
        parser.error("--train-ratio + --valid-ratio must be <= 1.0")

    random.seed(args.seed)

    # Load all sources
    all_records: list[dict] = []
    for source_path in args.sources:
        records = _load_jsonl(source_path)
        print(f"Loaded {len(records):,} records from {source_path}", file=sys.stderr)
        all_records.extend(records)

    if not all_records:
        print("ERROR: No records loaded from any source.", file=sys.stderr)
        sys.exit(1)

    # Deduplicate on (input, output) key
    seen: set[tuple[str, str]] = set()
    deduped: list[dict] = []
    for r in all_records:
        key = (r["input"].strip(), r["output"].strip())
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    duplicates_removed = len(all_records) - len(deduped)
    if duplicates_removed:
        print(f"Removed {duplicates_removed} duplicates.", file=sys.stderr)

    all_records = deduped

    # Cap if requested
    if args.max_samples and len(all_records) > args.max_samples:
        all_records = random.sample(all_records, args.max_samples)
        print(f"Capped to {args.max_samples} samples.", file=sys.stderr)

    # Shuffle
    random.shuffle(all_records)

    total = len(all_records)
    train_end = int(total * args.train_ratio)
    valid_end = train_end + int(total * args.valid_ratio)

    splits = {
        "train": all_records[:train_end],
        "valid": all_records[train_end:valid_end],
        "test": all_records[valid_end:],
    }

    print(f"\nTotal records: {total:,}", file=sys.stderr)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    for split_name, records in splits.items():
        out_path = args.output_dir / f"{split_name}.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for record in records:
                formatted = _format_pair(record["input"], record["output"])
                f.write(json.dumps(formatted, ensure_ascii=False) + "\n")
        print(f"  {split_name}: {len(records):,} → {out_path}", file=sys.stderr)

    print("\nDone.", file=sys.stderr)


if __name__ == "__main__":
    main()
