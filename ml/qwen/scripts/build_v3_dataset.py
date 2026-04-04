"""Build v3 dataset: v2 data + new filler data (initial/complex/semantic/backtrack)."""

import json
import pathlib
import random

SYSTEM_PROMPT = (
    "You are a speech-to-text post-processor. Fix Turkish/English ASR output: "
    "correct Turkish characters (ç, ş, ğ, ı, ö, ü), add punctuation, "
    "remove filler words (şey/yani/hani/işte/ee/aa) when they carry no meaning, "
    "handle backtracking and stuttering. Output ONLY the corrected text."
)

ROOT = pathlib.Path(__file__).parent.parent

# New filler data files
NEW_DATA_FILES = [
    ROOT / "data" / "filler_initial.jsonl",
    ROOT / "data" / "filler_complex.jsonl",
    ROOT / "data" / "filler_semantic.jsonl",
    ROOT / "data" / "filler_backtrack.jsonl",
]

# v2 formatted data (already in chat template format)
V2_FILES = {
    "train": ROOT / "datasets" / "v2" / "train.jsonl",
    "valid": ROOT / "datasets" / "v2" / "valid.jsonl",
    "test":  ROOT / "datasets" / "v2" / "test.jsonl",
}

OUT_DIR = ROOT / "datasets" / "v3"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def format_pair(inp: str, out: str) -> str:
    return json.dumps({
        "text": (
            f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n"
            f"<|im_start|>user\n{inp}<|im_end|>\n"
            f"<|im_start|>assistant\n{out}<|im_end|>"
        )
    }, ensure_ascii=False)


def load_new_pairs() -> list[str]:
    pairs = []
    for f in NEW_DATA_FILES:
        if not f.exists():
            print(f"WARNING: {f} not found, skipping")
            continue
        with f.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                pairs.append(format_pair(d["input"], d["output"]))
    return pairs


def load_v2(split: str) -> list[str]:
    f = V2_FILES[split]
    if not f.exists():
        return []
    with f.open(encoding="utf-8") as fh:
        return [l.strip() for l in fh if l.strip()]


def write_jsonl(path: pathlib.Path, lines: list[str]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for l in lines:
            f.write(l + "\n")


def main() -> None:
    random.seed(42)

    new_pairs = load_new_pairs()
    print(f"New filler pairs: {len(new_pairs)}")

    # Split new pairs: 85% train, 10% valid, 5% test
    random.shuffle(new_pairs)
    n = len(new_pairs)
    n_test  = max(1, int(n * 0.05))
    n_valid = max(1, int(n * 0.10))
    n_train = n - n_valid - n_test

    new_train = new_pairs[:n_train]
    new_valid = new_pairs[n_train:n_train + n_valid]
    new_test  = new_pairs[n_train + n_valid:]

    # Combine with v2
    train = load_v2("train") + new_train
    valid = load_v2("valid") + new_valid
    test  = load_v2("test")  + new_test

    random.shuffle(train)
    random.shuffle(valid)

    write_jsonl(OUT_DIR / "train.jsonl", train)
    write_jsonl(OUT_DIR / "valid.jsonl", valid)
    write_jsonl(OUT_DIR / "test.jsonl",  test)

    print(f"v3 dataset written to {OUT_DIR}")
    print(f"  train: {len(train)}")
    print(f"  valid: {len(valid)}")
    print(f"  test:  {len(test)}")
    print(f"  total: {len(train) + len(valid) + len(test)}")


if __name__ == "__main__":
    main()
