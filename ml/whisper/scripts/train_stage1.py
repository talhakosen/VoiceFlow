"""whisper_issai_finetune.py — Katman 1: ISSAI Turkish Speech Corpus ile whisper-large-v3-turbo fine-tune.

Sonuç: voiceflow-whisper-tr (merge edilmiş base model, ~1.5GB)
Bu model Katman 2'de IT kayıtlarıyla daha da fine-tune edilecek.

RunPod H100 80GB için optimize edilmiştir.

Kurulum (RunPod):
    pip install 'transformers==4.44.2' 'peft==0.12.0' datasets soundfile librosa evaluate accelerate -q

Çalıştırma:
    HF_TOKEN=xxx nohup python whisper_issai_finetune.py > /workspace/training.log 2>&1 &
    tail -f /workspace/training.log
"""

import os
import sys
import logging
import json
import tarfile
import csv
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
from datasets import Dataset
from peft import LoraConfig, get_peft_model

# ── Config ────────────────────────────────────────────────────────────────────

MODEL_NAME      = "openai/whisper-large-v3-turbo"
ISSAI_TAR       = Path("/root/issai/ISSAI_TSC_218.tar.gz")
ISSAI_EXTRACT   = Path("/root/issai/extracted")
OUTPUT_DIR      = Path("/root/training_out/whisper_issai_adapter")   # geçici checkpoints
MERGED_DIR      = Path("/workspace/voiceflow-whisper-tr")             # kalıcı: volume'a
SAMPLE_RATE     = 16000
MAX_LABEL_LEN   = 448
LANGUAGE        = "tr"
TASK            = "transcribe"

# H100 80GB
BATCH_SIZE      = 16
GRAD_ACCUM      = 2       # effective batch = 32
NUM_EPOCHS      = 3
LR              = 1e-3
WARMUP_STEPS    = 100
EVAL_STEPS      = 500
SAVE_STEPS      = 500


# ── Step 1: Download ──────────────────────────────────────────────────────────

def download_issai():
    """ISSAI tar.gz'yi HuggingFace'ten indir (token ile hızlı)."""
    if ISSAI_TAR.exists():
        log.info(f"ISSAI zaten indirilmiş: {ISSAI_TAR} ({ISSAI_TAR.stat().st_size/1024/1024/1024:.1f}GB)")
        return

    ISSAI_TAR.parent.mkdir(parents=True, exist_ok=True)
    log.info("ISSAI Turkish Speech Corpus indiriliyor (~20GB, birkaç dakika)...")

    from huggingface_hub import hf_hub_download
    path = hf_hub_download(
        repo_id="issai/Turkish_Speech_Corpus",
        filename="ISSAI_TSC_218.tar.gz",
        repo_type="dataset",
        local_dir=str(ISSAI_TAR.parent),
    )
    log.info(f"İndirme tamamlandı: {path}")


# ── Step 2: Extract ───────────────────────────────────────────────────────────

def extract_issai():
    """Tar.gz'yi çıkart."""
    if ISSAI_EXTRACT.exists() and any(ISSAI_EXTRACT.iterdir()):
        log.info(f"ISSAI zaten çıkartılmış: {ISSAI_EXTRACT}")
        return

    ISSAI_EXTRACT.mkdir(parents=True, exist_ok=True)
    log.info(f"Çıkartılıyor: {ISSAI_TAR} → {ISSAI_EXTRACT}")
    with tarfile.open(ISSAI_TAR, "r:gz") as tar:
        tar.extractall(str(ISSAI_EXTRACT))
    log.info("Çıkartma tamamlandı.")


# ── Step 3: Find transcription file ──────────────────────────────────────────

def find_pairs() -> list[dict]:
    """ISSAI yapısı: her WAV için aynı isimde TXT dosyası var.
    Train/ ve Test/ split'leri. Sadece Train kullanıyoruz.
    TXT içeriği: tek satır transcript, sonu '---' ile bitebilir.
    """
    # Sadece Train'i kullan (Test = eval için ayır)
    train_dir = ISSAI_EXTRACT / "ISSAI_TSC_218" / "Train"
    if not train_dir.exists():
        # Fallback: tüm dizini tara
        train_dir = ISSAI_EXTRACT

    log.info(f"Pair taranıyor: {train_dir}")
    pairs = []
    missing_txt = 0

    wav_files = sorted(train_dir.rglob("*.wav"))
    log.info(f"WAV dosyası: {len(wav_files)}")

    for wav in wav_files:
        txt = wav.with_suffix(".txt")
        if not txt.exists():
            missing_txt += 1
            continue
        transcript = txt.read_text(encoding="utf-8").strip().rstrip("-").strip()
        if not transcript:
            continue
        pairs.append({"audio": str(wav), "text": transcript})

    log.info(f"Pair: {len(pairs)}, TXT eksik: {missing_txt}")
    return pairs


# ── Step 4: On-the-fly Torch Dataset ─────────────────────────────────────────
# Preprocessing cache YOK — her batch training sırasında WAV'dan okunur.
# Disk: sadece modeller. RAM: sadece 1 batch. GPU: training boyunca dolu.

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
            # Bozuk dosya → sessizlik
            audio = np.zeros(SAMPLE_RATE, dtype="float32")

        feat = self.processor(audio, sampling_rate=SAMPLE_RATE, return_tensors="np")
        labels = self.processor.tokenizer(
            item["text"], max_length=MAX_LABEL_LEN, truncation=True
        ).input_ids
        return {
            "input_features": feat.input_features[0],
            "labels": labels,
        }


def prepare_dataset(processor, pairs: list[dict]):
    split_idx  = int(len(pairs) * 0.95)
    train_ds   = ISSAIDataset(pairs[:split_idx], processor)
    eval_ds    = ISSAIDataset(pairs[split_idx:],  processor)
    log.info(f"Train: {len(train_ds)}, Eval: {len(eval_ds)} (on-the-fly, disk cache yok)")
    return train_ds, eval_ds


# ── Data Collator ─────────────────────────────────────────────────────────────

class DataCollator:
    def __init__(self, processor):
        self.processor = processor

    def __call__(self, features):
        input_features = [{"input_features": f["input_features"]} for f in features]
        batch = self.processor.feature_extractor.pad(input_features, return_tensors="pt")

        label_features = [{"input_ids": f["labels"]} for f in features]
        labels_batch = self.processor.tokenizer.pad(label_features, return_tensors="pt")
        labels = labels_batch["input_ids"].masked_fill(
            labels_batch.attention_mask.ne(1), -100
        )
        if (labels[:, 0] == self.processor.tokenizer.bos_token_id).all().cpu().item():
            labels = labels[:, 1:]
        batch["labels"] = labels
        return batch


# ── Training ──────────────────────────────────────────────────────────────────

def train():
    log.info("=" * 60)
    log.info("VoiceFlow Whisper — Katman 1: ISSAI Fine-Tune")
    log.info(f"Model : {MODEL_NAME}")
    log.info(f"Output: {OUTPUT_DIR}")
    log.info(f"Merged: {MERGED_DIR}")
    log.info("=" * 60)

    # 1. İndir + çıkart
    download_issai()
    extract_issai()

    # 2. Pair'leri bul
    pairs = find_pairs()
    if not pairs:
        log.error("Hiç pair bulunamadı! ISSAI yapısını kontrol et.")
        sys.exit(1)
    log.info(f"Toplam pair: {len(pairs)}")

    # 3. Model + processor
    processor = WhisperProcessor.from_pretrained(MODEL_NAME, language=LANGUAGE, task=TASK)
    model = WhisperForConditionalGeneration.from_pretrained(MODEL_NAME)
    model.generation_config.language = LANGUAGE
    model.generation_config.task = TASK
    model.generation_config.forced_decoder_ids = None

    # 4. LoRA
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "v_proj", "k_proj", "out_proj"],
        lora_dropout=0.05,
        bias="none",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # 5. Dataset hazırla
    train_ds, eval_ds = prepare_dataset(processor, pairs)

    # 6. Training args — H100 optimize
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
        dataloader_num_workers=8,
        dataloader_pin_memory=True,
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

    log.info("\nTraining başlıyor...")
    trainer.train()

    # 7. Adapter kaydet (checkpoint)
    model.save_pretrained(str(OUTPUT_DIR / "final"))
    processor.save_pretrained(str(OUTPUT_DIR / "final"))
    log.info(f"LoRA adapter kaydedildi: {OUTPUT_DIR}/final")

    # 8. Merge → voiceflow-whisper-tr (volume'a)
    log.info("\nLoRA merge ediliyor → voiceflow-whisper-tr...")
    merged = model.merge_and_unload()
    MERGED_DIR.mkdir(parents=True, exist_ok=True)
    merged.save_pretrained(str(MERGED_DIR))
    processor.save_pretrained(str(MERGED_DIR))
    log.info(f"Merged model kaydedildi: {MERGED_DIR}")

    size_mb = sum(p.stat().st_size for p in MERGED_DIR.rglob("*") if p.is_file()) / 1024 / 1024
    log.info(f"Model boyutu: {size_mb:.0f} MB")
    log.info("Katman 1 TAMAMLANDI — voiceflow-whisper-tr hazır.")


if __name__ == "__main__":
    train()
