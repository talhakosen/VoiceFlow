"""prepare_v2_dataset.py — filler_pairs + existing sample → datasets/v2/

Mevcut train/valid'den 600 örnek al (catastrophic forgetting önlemi)
+ 496 yeni filler pair → karıştır → train/valid/test split → datasets/v2/
"""

import json, random
from pathlib import Path

random.seed(42)

ROOT = Path(__file__).parents[1]
DATA = ROOT / "data"
DATASETS = ROOT / "datasets"
OUT = ROOT / "datasets" / "v2"
OUT.mkdir(parents=True, exist_ok=True)

SYSTEM = (
    "You are a speech-to-text post-processor. Fix Turkish/English ASR output: "
    "correct Turkish characters (ç, ş, ğ, ı, ö, ü), add punctuation, "
    "remove filler words (şey/yani/hani/işte/ee/aa), handle backtracking and stuttering. "
    "Output ONLY the corrected text."
)

def fmt(inp: str, out: str) -> dict:
    text = (
        f"<|im_start|>system\n{SYSTEM}<|im_end|>\n"
        f"<|im_start|>user\n{inp}<|im_end|>\n"
        f"<|im_start|>assistant\n{out}<|im_end|>"
    )
    return {"text": text}

# 1. Yeni filler pair'leri yükle
filler = [json.loads(l) for l in (DATA / "filler_pairs.jsonl").read_text().splitlines() if l.strip()]
filler_fmt = [fmt(p["input"], p["output"]) for p in filler]
print(f"Filler pairs: {len(filler_fmt)}")

# 2. Mevcut train.jsonl'den 600 örnek sample al
existing = [json.loads(l) for l in (DATASETS / "train.jsonl").read_text().splitlines() if l.strip()]
existing_sample = random.sample(existing, min(600, len(existing)))
print(f"Existing sample: {len(existing_sample)}")

# 3. Birleştir ve karıştır
all_data = filler_fmt + existing_sample
random.shuffle(all_data)
print(f"Total: {len(all_data)}")

# 4. Split: %85 train, %10 valid, %5 test
n = len(all_data)
n_valid = max(30, int(n * 0.10))
n_test  = max(20, int(n * 0.05))
n_train = n - n_valid - n_test

splits = {
    "train": all_data[:n_train],
    "valid": all_data[n_train:n_train+n_valid],
    "test":  all_data[n_train+n_valid:],
}

for name, items in splits.items():
    path = OUT / f"{name}.jsonl"
    path.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in items) + "\n")
    print(f"  {name}: {len(items)} → {path}")

print("Done.")
