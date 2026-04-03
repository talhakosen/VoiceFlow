"""whisper_poc_finetune.py — Quick PoC: Fine-tune whisper-small with IT dataset recordings.

Uses PEFT LoRA on whisper-small for fast iteration on Mac.
Requires: transformers, peft, datasets, torch, soundfile, librosa

Usage:
    cd backend/scripts/data_gen
    python whisper_poc_finetune.py              # train
    python whisper_poc_finetune.py --eval-only  # eval only (after training)
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

os.environ["TOKENIZERS_PARALLELISM"] = "false"
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)

import soundfile as sf
import torch

# GPU: use CUDA if available
USE_CUDA = torch.cuda.is_available()
DEVICE = "cuda" if USE_CUDA else "cpu"
import numpy as np
from datasets import Dataset
from transformers import (
    WhisperProcessor,
    WhisperForConditionalGeneration,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
)
from peft import LoraConfig, get_peft_model, PeftModel
import evaluate

# ── Config ────────────────────────────────────────────────────────────────────

MODEL_NAME = "openai/whisper-small"
PAIRS_PATH = Path(__file__).parent / "it_dataset_pairs.jsonl"
OUTPUT_DIR = Path(__file__).parent / "whisper_poc_adapter"
SAMPLE_RATE = 16000
MAX_LABEL_LENGTH = 448


# ── Data Loading ──────────────────────────────────────────────────────────────

def load_pairs() -> list[dict]:
    pairs = []
    recordings_dir = PAIRS_PATH.parent / "it_recordings"
    with open(PAIRS_PATH) as f:
        for line in f:
            if not line.strip():
                continue
            p = json.loads(line)
            wav = p.get("wav_path", "")
            if not wav:
                continue
            wav_path = Path(wav)
            # If absolute path doesn't exist, try relative to recordings dir
            if not wav_path.exists():
                wav_path = recordings_dir / wav_path.name
            if wav_path.exists():
                pairs.append({"audio": str(wav_path), "text": p["output"]})
    return pairs


def _load_audio(path: str) -> np.ndarray:
    """Load audio file and resample to SAMPLE_RATE if needed."""
    audio, sr = sf.read(path, dtype="float32")
    if sr != SAMPLE_RATE:
        import librosa
        audio = librosa.resample(audio, orig_sr=sr, target_sr=SAMPLE_RATE)
    return audio


def prepare_dataset(processor):
    pairs = load_pairs()
    if not pairs:
        print("HATA: Kayıt bulunamadı!")
        sys.exit(1)

    # 80/20 split
    split = int(len(pairs) * 0.8)
    train_pairs = pairs[:split]
    eval_pairs = pairs[split:]
    print(f"Train: {len(train_pairs)}, Eval: {len(eval_pairs)}", flush=True)

    def make_dataset(data):
        processed = []
        for item in data:
            audio = _load_audio(item["audio"])
            inputs = processor(audio, sampling_rate=SAMPLE_RATE, return_tensors="np")
            labels = processor.tokenizer(
                item["text"], max_length=MAX_LABEL_LENGTH, truncation=True
            ).input_ids
            processed.append({
                "input_features": inputs.input_features[0],
                "labels": labels,
                "text": item["text"],
            })
        return Dataset.from_list(processed)

    train_ds = make_dataset(train_pairs)
    eval_ds = make_dataset(eval_pairs)
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
        # Remove BOS token if present
        if (labels[:, 0] == self.processor.tokenizer.bos_token_id).all():
            labels = labels[:, 1:]
        batch["labels"] = labels
        return batch


# ── Evaluation ────────────────────────────────────────────────────────────────

def evaluate_model(model, processor, eval_ds):
    """Run evaluation and print WER."""
    wer_metric = evaluate.load("wer")

    model.eval()
    predictions = []
    references = []

    for item in eval_ds:
        input_features = torch.tensor(item["input_features"]).unsqueeze(0).to(DEVICE)

        with torch.no_grad():
            predicted_ids = model.generate(
                input_features,
                language="tr",
                task="transcribe",
                max_new_tokens=128,
            )
        pred = processor.decode(predicted_ids[0], skip_special_tokens=True)
        ref = processor.decode(item["labels"], skip_special_tokens=True)
        predictions.append(pred)
        references.append(ref)
        print(f"  REF: {ref[:60]}")
        print(f"  PRD: {pred[:60]}")
        print()

    wer = wer_metric.compute(predictions=predictions, references=references)
    print(f"WER: {wer:.2%}")
    return wer


def evaluate_baseline(processor):
    """Evaluate base whisper-small WITHOUT fine-tuning."""
    print("\n" + "=" * 60)
    print("BASELINE (whisper-small, fine-tune yok)")
    print("=" * 60)

    model = WhisperForConditionalGeneration.from_pretrained(MODEL_NAME).to(DEVICE)

    pairs = load_pairs()
    split = int(len(pairs) * 0.8)
    eval_pairs = pairs[split:]

    wer_metric = evaluate.load("wer")
    predictions = []
    references = []

    for item in eval_pairs:
        audio = _load_audio(item["audio"])
        inputs = processor(audio, sampling_rate=SAMPLE_RATE, return_tensors="pt")
        inputs = {k: v.to(DEVICE) for k, v in inputs.items()}

        with torch.no_grad():
            predicted_ids = model.generate(
                inputs["input_features"],
                language="tr",
                task="transcribe",
                max_new_tokens=128,
            )
        pred = processor.decode(predicted_ids[0], skip_special_tokens=True)
        ref = item.get("text", "")
        predictions.append(pred)
        references.append(ref)
        print(f"  REF: {ref[:60]}")
        print(f"  PRD: {pred[:60]}")
        print()

    wer = wer_metric.compute(predictions=predictions, references=references)
    print(f"BASELINE WER: {wer:.2%}")
    return wer


# ── Training ──────────────────────────────────────────────────────────────────

def train():
    print(f"Device: {DEVICE} (CUDA: {USE_CUDA})")
    print(f"Model: {MODEL_NAME}")
    print(f"Dataset: {PAIRS_PATH}")
    print(f"Output: {OUTPUT_DIR}")
    print()

    processor = WhisperProcessor.from_pretrained(MODEL_NAME, language="tr", task="transcribe")

    # Baseline evaluation
    baseline_wer = evaluate_baseline(processor)

    # Load model
    model = WhisperForConditionalGeneration.from_pretrained(MODEL_NAME)
    model.generation_config.language = "tr"
    model.generation_config.task = "transcribe"
    model.generation_config.forced_decoder_ids = None

    # LoRA
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "v_proj", "k_proj", "out_proj"],
        lora_dropout=0.05,
        bias="none",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # Data
    train_ds, eval_ds = prepare_dataset(processor)

    # Training args
    training_args = Seq2SeqTrainingArguments(
        output_dir=str(OUTPUT_DIR),
        per_device_train_batch_size=4 if USE_CUDA else 1,
        gradient_accumulation_steps=2 if USE_CUDA else 1,
        learning_rate=1e-3,
        warmup_steps=5,
        num_train_epochs=3,
        eval_strategy="epoch",
        save_strategy="epoch",
        logging_steps=5,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        predict_with_generate=False,
        generation_max_length=128,
        fp16=USE_CUDA,
        report_to="none",
        remove_unused_columns=False,
    )

    # Trainer
    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        data_collator=DataCollator(processor),
        processing_class=processor,
    )

    print("\n🏋️ Training başlıyor...")
    trainer.train()

    # Save adapter
    model.save_pretrained(str(OUTPUT_DIR))
    processor.save_pretrained(str(OUTPUT_DIR))
    print(f"\n✅ Adapter kaydedildi: {OUTPUT_DIR}")

    # Final evaluation
    print("\n" + "=" * 60)
    print("FINE-TUNED MODEL")
    print("=" * 60)
    finetuned_wer = evaluate_model(model, processor, eval_ds)

    # Summary
    print("\n" + "=" * 60)
    print("SONUÇ")
    print("=" * 60)
    print(f"Baseline WER:    {baseline_wer:.2%}")
    print(f"Fine-tuned WER:  {finetuned_wer:.2%}")
    improvement = (baseline_wer - finetuned_wer) / baseline_wer * 100
    print(f"İyileşme:        {improvement:.1f}%")


def eval_only():
    processor = WhisperProcessor.from_pretrained(MODEL_NAME, language="tr", task="transcribe")

    # Baseline
    baseline_wer = evaluate_baseline(processor)

    # Fine-tuned
    print("\n" + "=" * 60)
    print("FINE-TUNED MODEL")
    print("=" * 60)
    base_model = WhisperForConditionalGeneration.from_pretrained(MODEL_NAME)
    model = PeftModel.from_pretrained(base_model, str(OUTPUT_DIR)).to(DEVICE)

    _, eval_ds = prepare_dataset(processor)
    finetuned_wer = evaluate_model(model, processor, eval_ds)

    print(f"\nBaseline: {baseline_wer:.2%} → Fine-tuned: {finetuned_wer:.2%}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-only", action="store_true")
    args = parser.parse_args()

    if args.eval_only:
        eval_only()
    else:
        train()


if __name__ == "__main__":
    main()
