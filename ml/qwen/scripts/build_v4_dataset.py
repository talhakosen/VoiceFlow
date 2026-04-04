"""Build v4 dataset: v3 data + persona data → datasets/v4/."""

import json
import pathlib
import random

SYSTEM_PROMPT = (
    "You are a speech-to-text post-processor. Fix Turkish/English ASR output: "
    "correct Turkish characters (ç, ş, ğ, ı, ö, ü), add punctuation, "
    "remove filler words (şey/yani/hani/işte/ee/aa) when they carry no meaning, "
    "fix phonetic misspellings of technical terms, "
    "handle backtracking and stuttering. Output ONLY the corrected text."
)

ROOT = pathlib.Path(__file__).parent.parent
DATA_DIR = ROOT / "data"

# v3 formatted data
V3_DIR = ROOT / "datasets" / "v3"
OUT_DIR = ROOT / "datasets" / "v4"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def format_pair(inp: str, out: str) -> str:
    return json.dumps({
        "text": (
            f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n"
            f"<|im_start|>user\n{inp}<|im_end|>\n"
            f"<|im_start|>assistant\n{out}<|im_end|>"
        )
    }, ensure_ascii=False)


def load_persona_pairs() -> list[str]:
    pairs = []
    for f in sorted(DATA_DIR.glob("persona_*.jsonl")):
        with f.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                pairs.append(format_pair(d["input"], d["output"]))
    return pairs


def load_v3(split: str) -> list[str]:
    f = V3_DIR / f"{split}.jsonl"
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

    persona_pairs = load_persona_pairs()
    print(f"Persona pairs: {len(persona_pairs)}")

    # Split: 85/10/5
    random.shuffle(persona_pairs)
    n = len(persona_pairs)
    n_test  = max(1, int(n * 0.05))
    n_valid = max(1, int(n * 0.10))
    n_train = n - n_valid - n_test

    new_train = persona_pairs[:n_train]
    new_valid = persona_pairs[n_train:n_train + n_valid]
    new_test  = persona_pairs[n_train + n_valid:]

    train = load_v3("train") + new_train
    valid = load_v3("valid") + new_valid
    test  = load_v3("test")  + new_test

    random.shuffle(train)
    random.shuffle(valid)

    write_jsonl(OUT_DIR / "train.jsonl", train)
    write_jsonl(OUT_DIR / "valid.jsonl", valid)
    write_jsonl(OUT_DIR / "test.jsonl",  test)

    print(f"v4 dataset → {OUT_DIR}")
    print(f"  train: {len(train)}")
    print(f"  valid: {len(valid)}")
    print(f"  test:  {len(test)}")
    print(f"  total: {len(train) + len(valid) + len(test)}")


if __name__ == "__main__":
    main()
