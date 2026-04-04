#!/usr/bin/env python3
"""
VoiceFlow Overnight Training Loop — Mac M4 local

Her round:
  1. Farklı corruption profile ile veri üret
  2. Kümülatif dataset birleştir
  3. mlx_lm.lora ile eğit (önceki adapter'dan devam)
  4. Val loss kontrol → iyileştiyse kaydet, kötüleştiyse geri al

Kullanım:
  nohup python3 ml/qwen/scripts/overnight_train.py > /tmp/voiceflow_overnight.log 2>&1 &

İzleme:
  tail -f /tmp/voiceflow_overnight.log
"""

import json
import os
import pathlib
import random
import shutil
import subprocess
import sys
import time
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────

MAX_ROUNDS = 10
MAX_HOURS = 10
ITERS_PER_ROUND = 500
BASE_LR = 1e-5
LR_DECAY = 0.92  # her round %8 azalt
MODEL = "mlx-community/Qwen2.5-7B-Instruct-4bit"
BATCH_SIZE = 1
MAX_SEQ_LEN = 512
MIN_FREE_MEM_GB = 2.0       # Bu kadar boş bellek yoksa round'u atla
COOLDOWN_BETWEEN_ROUNDS = 30  # Round arası bekleme (saniye) — bellek temizlenmesi için
TELEGRAM_BOT_TOKEN = "8739980423:AAGiZD0ZFu7BwEK9XSSixFlvHnE5Ql8XPXY"
TELEGRAM_CHAT_ID = "1410531590"

ROOT = pathlib.Path(__file__).parents[3]  # voiceflow/
QWEN_DIR = ROOT / "ml" / "qwen"
DATA_DIR = QWEN_DIR / "data"
DATASETS_DIR = QWEN_DIR / "datasets"
ADAPTERS_DIR = QWEN_DIR / "adapters"
GENERATORS_DIR = QWEN_DIR / "generators"

# Add generators to path for imports
sys.path.insert(0, str(GENERATORS_DIR))

SYSTEM_PROMPT = (
    "You are a speech-to-text post-processor. Fix Turkish/English ASR output: "
    "correct Turkish characters (ç, ş, ğ, ı, ö, ü), add punctuation, "
    "remove filler words (şey/yani/hani/işte/ee/aa) when they carry no meaning, "
    "fix phonetic misspellings of technical terms, "
    "handle backtracking and stuttering. Output ONLY the corrected text."
)

# ── Corruption profiles — her round farklı ağırlıklar ────────────────────────

# Ofis odaklı profiller — teknik terim yok, filler/noktalama/büyük harf/devrik odak
CORRUPTION_PROFILES = [
    {"name": "balanced",       "punct_rate": 0.5, "cap_rate": 0.6, "filler_boost": False, "variants": 5},
    {"name": "filler_heavy",   "punct_rate": 0.3, "cap_rate": 0.4, "filler_boost": True,  "variants": 6},
    {"name": "punct_focus",    "punct_rate": 0.8, "cap_rate": 0.9, "filler_boost": False, "variants": 5},
    {"name": "light",          "punct_rate": 0.3, "cap_rate": 0.3, "filler_boost": False, "variants": 5},
    {"name": "extreme_filler", "punct_rate": 0.6, "cap_rate": 0.7, "filler_boost": True,  "variants": 7},
    {"name": "no_punct",       "punct_rate": 0.9, "cap_rate": 0.5, "filler_boost": False, "variants": 5},
    {"name": "mixed",          "punct_rate": 0.5, "cap_rate": 0.6, "filler_boost": True,  "variants": 7},
    {"name": "gentle",         "punct_rate": 0.2, "cap_rate": 0.2, "filler_boost": False, "variants": 4},
    {"name": "real_world",     "punct_rate": 0.5, "cap_rate": 0.5, "filler_boost": True,  "variants": 8},
    {"name": "final_push",     "punct_rate": 0.5, "cap_rate": 0.6, "filler_boost": True,  "variants": 9},
]

# ── Logging ───────────────────────────────────────────────────────────────────

def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def log_separator():
    print("=" * 70, flush=True)


def telegram(msg: str):
    """Telegram'a bildirim gönder."""
    try:
        import urllib.request, urllib.parse
        data = urllib.parse.urlencode({
            "chat_id": TELEGRAM_CHAT_ID,
            "text": msg,
            "parse_mode": "Markdown",
        }).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            data=data,
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass  # Telegram fail etse de eğitim durmasın


def get_available_memory_gb() -> float:
    """macOS'ta kullanılabilir bellek (free + inactive) GB cinsinden."""
    try:
        r = subprocess.run(["vm_stat"], capture_output=True, text=True)
        import re
        lines = r.stdout.strip().split("\n")
        page_size = 16384  # Apple Silicon
        free = int(re.search(r"(\d+)", lines[1]).group(1)) * page_size
        inactive = int(re.search(r"(\d+)", lines[3]).group(1)) * page_size
        return (free + inactive) / (1024 ** 3)
    except Exception:
        return 99.0  # Parse fail → devam et


def wait_for_memory(min_gb: float, max_wait: int = 120):
    """Bellek min_gb altındaysa bekle, max_wait saniye sonra devam et."""
    waited = 0
    while waited < max_wait:
        avail = get_available_memory_gb()
        if avail >= min_gb:
            return avail
        log(f"  ⏳ Bellek düşük ({avail:.1f}GB < {min_gb}GB), 15s bekliyorum...")
        time.sleep(15)
        waited += 15
    return get_available_memory_gb()


# ── Step 1: Generate data with specific corruption profile ────────────────────

def generate_round_data(round_num: int, profile: dict) -> int:
    """Generate office-focused data with corruption profile. Returns pair count."""
    from phonetic_corruptions import (
        corrupt_punctuation, corrupt_capitalization, add_fillers,
    )
    from gen_office_data import ALL_CATEGORIES
    from gen_persona_data import ALL_SCENARIOS

    seed = 42 + round_num * 1000
    random.seed(seed)

    all_pairs = []
    seen = set()

    # ── Office data: filler/noktalama/büyük harf varyantları ──────────────
    for cat_name, cat_pairs in ALL_CATEGORIES.items():
        for v in range(profile["variants"]):
            for inp, correct in cat_pairs:
                random.seed(hash((correct, v, cat_name, round_num)) & 0xFFFFFFFF)

                # Office data zaten bozuk input içeriyor — ek bozukluk uygula
                corrupted = inp
                corrupted = corrupt_punctuation(corrupted, prob=profile["punct_rate"])
                corrupted = corrupt_capitalization(corrupted, prob=profile["cap_rate"])
                corrupted = " ".join(corrupted.split())

                if corrupted not in seen:
                    seen.add(corrupted)
                    all_pairs.append({"input": corrupted, "output": correct})

    # ── Persona data (ofis senaryoları): sadece noktalama/büyük harf bozuklukları
    for scenario_name, sentences in ALL_SCENARIOS.items():
        for v in range(max(2, profile["variants"] // 2)):
            for filler_freq, correct in sentences:
                random.seed(hash((correct, v, scenario_name, round_num)) & 0xFFFFFFFF)

                corrupted = correct
                corrupted = corrupt_punctuation(corrupted, prob=profile["punct_rate"])
                corrupted = corrupt_capitalization(corrupted, prob=profile["cap_rate"])

                effective_freq = filler_freq
                if profile["filler_boost"] and filler_freq == "low":
                    effective_freq = "medium"
                elif profile["filler_boost"] and filler_freq == "medium":
                    effective_freq = "high"
                corrupted = add_fillers(corrupted, effective_freq)
                corrupted = " ".join(corrupted.split())

                if corrupted.strip() == correct.strip():
                    corrupted = correct.lower().replace(".", "").replace(",", "").replace("?", "").replace("!", "")

                if corrupted not in seen:
                    seen.add(corrupted)
                    all_pairs.append({"input": corrupted, "output": correct})

    random.seed(42)

    # Write round-specific file
    out_file = DATA_DIR / f"round_{round_num:02d}.jsonl"
    with out_file.open("w", encoding="utf-8") as f:
        for pair in all_pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    return len(all_pairs)


# ── Step 2: Build cumulative dataset ──────────────────────────────────────────

def format_pair(inp: str, out: str) -> str:
    return json.dumps({
        "text": (
            f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n"
            f"<|im_start|>user\n{inp}<|im_end|>\n"
            f"<|im_start|>assistant\n{out}<|im_end|>"
        )
    }, ensure_ascii=False)


def build_dataset(round_num: int) -> tuple[int, pathlib.Path]:
    """Build cumulative dataset from v3 base + all round files."""
    random.seed(42)

    # Load v3 base
    v3_train = DATASETS_DIR / "v3" / "train.jsonl"
    v3_valid = DATASETS_DIR / "v3" / "valid.jsonl"
    v3_test = DATASETS_DIR / "v3" / "test.jsonl"

    base_train = [l.strip() for l in v3_train.open() if l.strip()] if v3_train.exists() else []
    base_valid = [l.strip() for l in v3_valid.open() if l.strip()] if v3_valid.exists() else []
    base_test = [l.strip() for l in v3_test.open() if l.strip()] if v3_test.exists() else []

    # Load existing filler + office data
    new_pairs = []
    for f in sorted(DATA_DIR.glob("office_*.jsonl")):
        with f.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    d = json.loads(line)
                    new_pairs.append(format_pair(d["input"], d["output"]))

    for f in sorted(DATA_DIR.glob("filler_*.jsonl")):
        with f.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    d = json.loads(line)
                    new_pairs.append(format_pair(d["input"], d["output"]))

    # Load persona base data
    for f in sorted(DATA_DIR.glob("persona_*.jsonl")):
        with f.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    d = json.loads(line)
                    new_pairs.append(format_pair(d["input"], d["output"]))

    # Load ALL round data (cumulative)
    for r in range(1, round_num + 1):
        rf = DATA_DIR / f"round_{r:02d}.jsonl"
        if rf.exists():
            with rf.open(encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        d = json.loads(line)
                        new_pairs.append(format_pair(d["input"], d["output"]))

    # Split new pairs
    random.shuffle(new_pairs)
    n = len(new_pairs)
    n_test = max(1, int(n * 0.05))
    n_valid = max(1, int(n * 0.10))
    n_train = n - n_valid - n_test

    train = base_train + new_pairs[:n_train]
    valid = base_valid + new_pairs[n_train:n_train + n_valid]
    test = base_test + new_pairs[n_train + n_valid:]

    random.shuffle(train)
    random.shuffle(valid)

    # Write to round-specific dataset dir
    out_dir = DATASETS_DIR / f"round_{round_num:02d}"
    out_dir.mkdir(parents=True, exist_ok=True)

    for name, data in [("train", train), ("valid", valid), ("test", test)]:
        with (out_dir / f"{name}.jsonl").open("w", encoding="utf-8") as f:
            for line in data:
                f.write(line + "\n")

    total = len(train) + len(valid) + len(test)
    return total, out_dir


# ── Step 3: Train ─────────────────────────────────────────────────────────────

def train_round(round_num: int, dataset_dir: pathlib.Path, lr: float, resume_from: pathlib.Path | None) -> tuple[float, pathlib.Path]:
    """Run mlx_lm.lora training. Returns (val_loss, adapter_path)."""
    adapter_path = ADAPTERS_DIR / f"v4.{round_num}"
    adapter_path.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable, "-u", "-m", "mlx_lm.lora",
        "--model", MODEL,
        "--train",
        "--data", str(dataset_dir),
        "--fine-tune-type", "lora",
        "--batch-size", str(BATCH_SIZE),
        "--iters", str(ITERS_PER_ROUND),
        "--learning-rate", str(lr),
        "--steps-per-report", "100",
        "--steps-per-eval", str(ITERS_PER_ROUND),  # eval only at end
        "--save-every", str(ITERS_PER_ROUND),
        "--max-seq-length", str(MAX_SEQ_LEN),
        "--grad-checkpoint",
        "--adapter-path", str(adapter_path),
    ]

    if resume_from and (resume_from / "adapters.safetensors").exists():
        cmd.extend(["--resume-adapter-file", str(resume_from / "adapters.safetensors")])

    log(f"  Training: iters={ITERS_PER_ROUND}, lr={lr:.2e}, adapter={adapter_path.name}")
    if resume_from:
        log(f"  Resume from: {resume_from.name}")

    log_file = pathlib.Path(f"/tmp/voiceflow_round_{round_num:02d}.log")

    with log_file.open("w") as lf:
        proc = subprocess.run(
            cmd,
            stdout=lf,
            stderr=subprocess.STDOUT,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
            cwd=str(ROOT),
        )

    if proc.returncode != 0:
        log(f"  ERROR: Training failed (exit {proc.returncode})")
        log(f"  Check: {log_file}")
        return float("inf"), adapter_path

    # Parse val loss from log
    val_loss = float("inf")
    with log_file.open() as f:
        for line in f:
            if "Val loss" in line:
                try:
                    val_loss = float(line.split("Val loss")[1].split(",")[0].strip())
                except (ValueError, IndexError):
                    pass

    # Parse train loss
    train_loss = float("inf")
    with log_file.open() as f:
        for line in f:
            if "Train loss" in line and f"Iter {ITERS_PER_ROUND}:" in line:
                try:
                    train_loss = float(line.split("Train loss")[1].split(",")[0].strip())
                except (ValueError, IndexError):
                    pass

    log(f"  Val loss: {val_loss:.4f}, Train loss: {train_loss:.4f}")
    log(f"  Log: {log_file}")

    return val_loss, adapter_path


# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    start_time = time.time()
    max_seconds = MAX_HOURS * 3600

    log_separator()
    log("VoiceFlow Overnight Training Loop")
    log(f"Max rounds: {MAX_ROUNDS}, Max hours: {MAX_HOURS}")
    log(f"Model: {MODEL}")
    log(f"Base LR: {BASE_LR}, Decay: {LR_DECAY}")
    log(f"Iters per round: {ITERS_PER_ROUND}")
    log(f"Min free memory: {MIN_FREE_MEM_GB}GB")
    log_separator()

    telegram(f"🚀 *Overnight Training BAŞLADI*\n⏱ {MAX_ROUNDS} round × {ITERS_PER_ROUND} iter\n🖥 Mac M4, min {MIN_FREE_MEM_GB}GB free mem guard")

    best_val_loss = 0.428  # v4.0 baseline
    best_adapter = ADAPTERS_DIR / "v4.0"
    results = []

    for round_num in range(1, MAX_ROUNDS + 1):
        elapsed = time.time() - start_time
        if elapsed > max_seconds:
            log(f"Time limit reached ({MAX_HOURS}h). Stopping.")
            break

        remaining_h = (max_seconds - elapsed) / 3600
        log_separator()
        log(f"ROUND {round_num}/{MAX_ROUNDS} (elapsed: {elapsed/3600:.1f}h, remaining: {remaining_h:.1f}h)")
        log_separator()

        # ── Memory guard ──────────────────────────────────────────────────
        avail = wait_for_memory(MIN_FREE_MEM_GB)
        if avail < MIN_FREE_MEM_GB:
            log(f"  ⛔ Bellek yetersiz ({avail:.1f}GB). Round atlanıyor.")
            telegram(f"⛔ Round {round_num} atlandı — bellek {avail:.1f}GB < {MIN_FREE_MEM_GB}GB")
            continue

        log(f"  Memory: {avail:.1f}GB available")

        profile = CORRUPTION_PROFILES[(round_num - 1) % len(CORRUPTION_PROFILES)]
        lr = BASE_LR * (LR_DECAY ** (round_num - 1))

        # Step 1: Generate data
        log(f"  Profile: {profile['name']} (punct={profile['punct_rate']}, cap={profile['cap_rate']}, filler_boost={profile['filler_boost']}, variants={profile['variants']})")
        pair_count = generate_round_data(round_num, profile)
        log(f"  Generated: {pair_count} new pairs")

        # Step 2: Build dataset
        total, dataset_dir = build_dataset(round_num)
        log(f"  Dataset: {total} total pairs → {dataset_dir.name}")

        # Step 3: Train
        resume_from = best_adapter if round_num > 1 else None
        telegram(f"🔄 *Round {round_num}* başlıyor\n📊 {total} pair, lr={lr:.2e}\n🎯 Profile: {profile['name']}")
        val_loss, adapter_path = train_round(round_num, dataset_dir, lr, resume_from)

        # Step 4: Decide
        if val_loss < best_val_loss and val_loss != float("inf"):
            improvement = (best_val_loss - val_loss) / best_val_loss * 100
            log(f"  ✅ IMPROVED: {best_val_loss:.4f} → {val_loss:.4f} ({improvement:.1f}%)")
            telegram(f"✅ *Round {round_num} İYİLEŞTİ*\nval\\_loss: {best_val_loss:.4f} → *{val_loss:.4f}* ({improvement:.1f}%↑)")
            best_val_loss = val_loss
            best_adapter = adapter_path
        elif val_loss == float("inf"):
            log(f"  ❌ FAILED — keeping best: {best_adapter.name} ({best_val_loss:.4f})")
            telegram(f"❌ Round {round_num} FAILED — best: {best_adapter.name} ({best_val_loss:.4f})")
        else:
            regression = (val_loss - best_val_loss) / best_val_loss * 100
            log(f"  ⚠️  NO IMPROVEMENT: {val_loss:.4f} vs best {best_val_loss:.4f} (+{regression:.1f}%)")
            log(f"  Keeping best: {best_adapter.name}")
            telegram(f"⚠️ Round {round_num}: {val_loss:.4f} (best: {best_val_loss:.4f})")

        results.append({
            "round": round_num,
            "profile": profile["name"],
            "pairs": pair_count,
            "total_data": total,
            "lr": lr,
            "val_loss": val_loss,
            "best_val_loss": best_val_loss,
            "best_adapter": best_adapter.name,
            "elapsed_h": elapsed / 3600,
        })

        # ── Cooldown — bellek temizlenmesi için bekle ─────────────────────
        if round_num < MAX_ROUNDS:
            log(f"  💤 {COOLDOWN_BETWEEN_ROUNDS}s cooldown...")
            time.sleep(COOLDOWN_BETWEEN_ROUNDS)

        log("")

    # ── Summary ───────────────────────────────────────────────────────────────
    total_time_h = (time.time() - start_time) / 3600
    log_separator()
    log("OVERNIGHT TRAINING COMPLETE")
    log_separator()
    log(f"Rounds completed: {len(results)}")
    log(f"Best val loss: {best_val_loss:.4f}")
    log(f"Best adapter: {best_adapter}")
    log(f"Total time: {total_time_h:.1f}h")
    log("")
    log("Round results:")
    summary_lines = []
    for r in results:
        marker = "✅" if r["val_loss"] == r["best_val_loss"] else "  "
        line = f"  {marker} Round {r['round']:2d}: val={r['val_loss']:.4f} | data={r['total_data']:5d} | lr={r['lr']:.2e} | profile={r['profile']}"
        log(line)
        summary_lines.append(f"R{r['round']}: {r['val_loss']:.3f} ({r['profile']})")

    log("")
    log(f"To activate best adapter:")
    log(f"  config.yaml → adapter_path: ml/qwen/{best_adapter.relative_to(ROOT / 'ml' / 'qwen')}")
    log_separator()

    # Save results
    results_file = QWEN_DIR / "overnight_results.json"
    with results_file.open("w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    log(f"Results saved to {results_file}")

    # Final Telegram
    telegram(
        f"🏁 *Overnight Training BİTTİ*\n"
        f"⏱ {total_time_h:.1f} saat, {len(results)} round\n"
        f"🏆 Best: *{best_val_loss:.4f}* ({best_adapter.name})\n\n"
        + "\n".join(summary_lines)
    )


if __name__ == "__main__":
    main()
