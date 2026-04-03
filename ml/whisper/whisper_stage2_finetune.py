"""whisper_stage2_finetune.py — Katman 2: voiceflow-whisper-tr üstüne noktalama fine-tune.

Base  : tkosen/voiceflow-whisper-tr (ISSAI 164K ile eğitilmiş, Stage 1 çıktısı)
Hedef : Aynı WAV'lar + noktalı/büyük harfli text → decoder noktalama öğrenir
Sonuç : voiceflow-whisper-tr-v2 (~1.5GB merged)

Neden düşük LR (5e-6)?
  Stage 1 akustik Türkçe'yi öğretti. Stage 2 sadece decoder çıktısını
  güncelliyor (noktalama/büyük harf). Yüksek LR → catastrophic forgetting.

── H100 80GB optimize edilmiş komutlar ──────────────────────────────────────────

# 0. Deps
pip install 'transformers==4.44.2' 'peft==0.12.0' soundfile librosa accelerate bitsandbytes -q

# 1. issai_punctuated.jsonl yükle (lokal'den ~35MB)
scp ml/whisper/datasets/issai/issai_punctuated.jsonl root@<pod>:/workspace/
scp ml/whisper/whisper_stage2_finetune.py root@<pod>:/workspace/

# 2. RAM disk trick — I/O darboğazını kaldır (ISSAI WAV'lar ~26GB, RAM'e sığar)
free -h                                              # RAM kontrolü (genelde 200GB+)
mkdir -p /dev/shm/issai
cp -r /workspace/issai/extracted /dev/shm/issai/    # veya /root/issai/extracted varsa
# (cp ~30-60 saniye sürer, ama training süresini ~1 saat kısaltır)

# 3. Çalıştır
cd /workspace
HF_TOKEN=xxx nohup python whisper_stage2_finetune.py > /workspace/stage2.log 2>&1 &
tail -f /workspace/stage2.log
"""

import os
import sys
import logging
import json
import tarfile
from pathlib import Path

os.environ["TOKENIZERS_PARALLELISM"] = "false"
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stderr)
log = logging.getLogger(__name__)

import numpy as np
import torch
from torch.utils.data import Dataset as TorchDataset
import soundfile as sf
from transformers import (
    WhisperProcessor,
    WhisperForConditionalGeneration,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
)
from peft import LoraConfig, get_peft_model

# ── Config ────────────────────────────────────────────────────────────────────

MODEL_NAME          = "tkosen/voiceflow-whisper-tr"

# issai_punctuated.jsonl Whisper ASR outputlarından oluşturuldu (Qwen training için).
# WAV ground truth TXT dosyaları farklı → lookup eşleşmiyor.
# Bunun yerine _clean_gt() ile TXT dosyasını doğrudan işliyoruz.

# WAV arama sırası: RAM disk → /root (container SSD, hızlı) → /workspace (kalıcı NFS)
_ISSAI_CANDIDATES = [
    Path("/dev/shm/issai/extracted"),        # RAM disk (en hızlı)
    Path("/root/issai/extracted"),           # Container SSD — yeni pod, extraction buraya
    Path("/workspace/issai/extracted"),      # NFS volume — yavaş ama kalıcı
]

# ── Ground truth temizleme ────────────────────────────────────────────────────
_FILLERS = {"ee", "aa", "hmm", "hm", "ıı", "mm", "ah", "eh", "uh", "um"}

def _clean_gt(text: str) -> str:
    """ISSAI TXT ground truth: filler sil, büyük harf (Türkçe i→İ), nokta ekle."""
    text = text.strip().rstrip("-").strip()
    if not text:
        return ""
    words = text.split()
    cleaned = [w for w in words if w.lower().rstrip(".,!?") not in _FILLERS]
    if not cleaned:
        return ""
    result = " ".join(cleaned)
    # Türkçe büyük harf kuralı
    if result[0] == "i":
        result = "İ" + result[1:]
    elif result[0] == "ı":
        result = "I" + result[1:]
    else:
        result = result[0].upper() + result[1:]
    if result[-1] not in ".!?…":
        result += "."
    return result

OUTPUT_DIR      = Path("/root/training_out/whisper_stage2")
MERGED_DIR      = Path("/workspace/voiceflow-whisper-tr-v2")
SAMPLE_RATE     = 16000
MAX_LABEL_LEN   = 448
LANGUAGE        = "tr"
TASK            = "transcribe"

# H100 80GB — optimize edilmiş
BATCH_SIZE      = 32    # Stage 1=16 → 32 (H100 80GB'de memory sorun yok, daha az step)
GRAD_ACCUM      = 1     # effective batch = 32 (accum gereksiz, batch direkt 2×)
NUM_EPOCHS      = 2     # Stage 1=3, Stage 2=2
LR              = 5e-6  # catastrophic forgetting önle
WARMUP_STEPS    = 50
EVAL_STEPS      = 500
SAVE_STEPS      = 500


# ── ISSAI path detection ──────────────────────────────────────────────────────

def find_issai_dir() -> Path:
    for candidate in _ISSAI_CANDIDATES:
        if candidate.exists() and any(candidate.rglob("*.wav")):
            log.info(f"ISSAI WAV'lar: {candidate}")
            return candidate

    # Fallback: indir
    log.info("ISSAI bulunamadı — HuggingFace'ten indiriliyor (~20GB)...")
    tar_path = Path("/workspace/issai/ISSAI_TSC_218.tar.gz")
    extract_to = Path("/workspace/issai/extracted")
    tar_path.parent.mkdir(parents=True, exist_ok=True)

    from huggingface_hub import hf_hub_download
    hf_hub_download(
        repo_id="issai/Turkish_Speech_Corpus",
        filename="ISSAI_TSC_218.tar.gz",
        repo_type="dataset",
        local_dir=str(tar_path.parent),
        token=os.getenv("HF_TOKEN"),
    )
    extract_to.mkdir(parents=True, exist_ok=True)
    log.info("Çıkartılıyor...")
    with tarfile.open(tar_path, "r:gz") as tar:
        tar.extractall(str(extract_to))

    return extract_to


# ── Find WAV+text pairs ───────────────────────────────────────────────────────

def find_pairs(issai_dir: Path) -> list[dict]:
    """WAV + ground truth TXT eşleştir. _clean_gt() ile temel noktalama ekle."""
    train_dir = issai_dir / "ISSAI_TSC_218" / "Train"
    if not train_dir.exists():
        train_dir = issai_dir

    log.info(f"WAV taranıyor: {train_dir}")
    pairs, missing_txt, empty = [], 0, 0

    for wav in sorted(train_dir.rglob("*.wav")):
        txt = wav.with_suffix(".txt")
        if not txt.exists():
            missing_txt += 1
            continue
        raw = txt.read_text(encoding="utf-8")
        text = _clean_gt(raw)
        if not text:
            empty += 1
            continue
        pairs.append({"audio": str(wav), "text": text})

    log.info(f"Pair: {len(pairs)} | TXT eksik: {missing_txt} | Boş: {empty}")
    return pairs


# ── Dataset ───────────────────────────────────────────────────────────────────

class ISSAIDataset(TorchDataset):
    def __init__(self, pairs: list[dict], processor):
        self.pairs     = pairs
        self.processor = processor

    def __len__(self):
        return len(self.pairs)

    def __getitem__(self, idx):
        item = self.pairs[idx]
        try:
            audio, sr = sf.read(item["audio"], dtype="float32")
            if audio.ndim > 1:
                audio = audio.mean(axis=1)
            if sr != SAMPLE_RATE:
                import librosa
                audio = librosa.resample(audio, orig_sr=sr, target_sr=SAMPLE_RATE)
        except Exception:
            audio = np.zeros(SAMPLE_RATE, dtype="float32")

        feat = self.processor(audio, sampling_rate=SAMPLE_RATE, return_tensors="np")
        labels = self.processor.tokenizer(
            item["text"], max_length=MAX_LABEL_LEN, truncation=True
        ).input_ids
        return {"input_features": feat.input_features[0], "labels": labels}


# ── Data Collator ─────────────────────────────────────────────────────────────

class DataCollator:
    def __init__(self, processor):
        self.processor = processor

    def __call__(self, features):
        input_features = [{"input_features": f["input_features"]} for f in features]
        batch = self.processor.feature_extractor.pad(input_features, return_tensors="pt")
        label_features = [{"input_ids": f["labels"]} for f in features]
        labels_batch = self.processor.tokenizer.pad(label_features, return_tensors="pt")
        labels = labels_batch["input_ids"].masked_fill(labels_batch.attention_mask.ne(1), -100)
        if (labels[:, 0] == self.processor.tokenizer.bos_token_id).all().cpu().item():
            labels = labels[:, 1:]
        batch["labels"] = labels
        return batch


# ── Training ──────────────────────────────────────────────────────────────────

def train():
    log.info("=" * 60)
    log.info("VoiceFlow Whisper — Katman 2: Noktalama Fine-Tune")
    log.info(f"Base    : {MODEL_NAME}")
    log.info(f"LR      : {LR}  (Stage 1'den 200× düşük)")
    log.info(f"Batch   : {BATCH_SIZE} × {GRAD_ACCUM} = {BATCH_SIZE * GRAD_ACCUM} effective")
    log.info(f"Epoch   : {NUM_EPOCHS}")
    log.info(f"Merged  : {MERGED_DIR}")
    log.info("=" * 60)

    hf_token = os.getenv("HF_TOKEN")

    # 1. ISSAI'yi bul (RAM disk > /root > /workspace > indir)
    issai_dir = find_issai_dir()

    # 2. WAV+GT pair'leri bul (_clean_gt ile temel noktalama)
    pairs = find_pairs(issai_dir)
    if not pairs:
        log.error("Hiç pair bulunamadı!")
        sys.exit(1)

    split_idx   = int(len(pairs) * 0.95)
    train_pairs = pairs[:split_idx]
    eval_pairs  = pairs[split_idx:]
    log.info(f"Train: {len(train_pairs)}, Eval: {len(eval_pairs)}")

    # 4. Model + processor
    processor = WhisperProcessor.from_pretrained(MODEL_NAME, language=LANGUAGE, task=TASK, token=hf_token)
    model = WhisperForConditionalGeneration.from_pretrained(MODEL_NAME, token=hf_token)
    model.generation_config.language = LANGUAGE
    model.generation_config.task = TASK
    model.generation_config.forced_decoder_ids = None

    # 5. LoRA — Stage 2: r=8 (Stage 1=16, daha az parametre = daha az forgetting riski)
    lora_config = LoraConfig(
        r=8,
        lora_alpha=16,
        target_modules=["q_proj", "v_proj", "k_proj", "out_proj"],
        lora_dropout=0.05,
        bias="none",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    train_ds = ISSAIDataset(train_pairs, processor)
    eval_ds  = ISSAIDataset(eval_pairs, processor)

    # 6. Training args — H100 maximize
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    training_args = Seq2SeqTrainingArguments(
        output_dir=str(OUTPUT_DIR),
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRAD_ACCUM,
        learning_rate=LR,
        warmup_steps=WARMUP_STEPS,
        num_train_epochs=NUM_EPOCHS,
        evaluation_strategy="steps",
        eval_steps=EVAL_STEPS,
        save_strategy="steps",
        save_steps=SAVE_STEPS,
        logging_steps=50,
        load_best_model_at_end=False,
        predict_with_generate=False,
        bf16=True,
        tf32=True,
        # ── H100 hız optimizasyonları ──────────────────────────────────
        optim="adamw_bnb_8bit",          # 8-bit Adam: optimizer memory küçük, hızlı
        torch_compile=True,              # inductor JIT: ~20% GPU hızlanması
        torch_compile_backend="inductor",
        dataloader_num_workers=16,       # Stage 1=8, 2× worker → CPU darboğazı azalır
        dataloader_pin_memory=True,
        dataloader_prefetch_factor=4,    # 4 batch önceden hazırla → GPU sürekli dolu
        # gradient_checkpointing=False   # Gerek yok: 80GB'da zaten sığıyor
        # ──────────────────────────────────────────────────────────────
        report_to="none",
        remove_unused_columns=False,
        save_total_limit=2,
    )

    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        data_collator=DataCollator(processor),
        tokenizer=processor.feature_extractor,
    )

    log.info("\nStage 2 training başlıyor...")
    trainer.train()

    # 7. Adapter + merge
    model.save_pretrained(str(OUTPUT_DIR / "final"))
    processor.save_pretrained(str(OUTPUT_DIR / "final"))
    log.info(f"LoRA adapter: {OUTPUT_DIR}/final")

    log.info("\nMerge ediliyor → voiceflow-whisper-tr-v2...")
    merged = model.merge_and_unload()
    MERGED_DIR.mkdir(parents=True, exist_ok=True)
    merged.save_pretrained(str(MERGED_DIR))
    processor.save_pretrained(str(MERGED_DIR))

    size_mb = sum(p.stat().st_size for p in MERGED_DIR.rglob("*") if p.is_file()) / 1024 / 1024
    log.info(f"Model boyutu: {size_mb:.0f} MB")
    log.info("Katman 2 TAMAMLANDI — voiceflow-whisper-tr-v2 hazır.")

    # 8. HF push
    if hf_token:
        log.info("\nHuggingFace'e yükleniyor: tkosen/voiceflow-whisper-tr-v2...")
        merged.push_to_hub("tkosen/voiceflow-whisper-tr-v2", token=hf_token)
        processor.push_to_hub("tkosen/voiceflow-whisper-tr-v2", token=hf_token)
        log.info("HF upload tamamlandı.")


if __name__ == "__main__":
    train()
