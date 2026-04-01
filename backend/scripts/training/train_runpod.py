"""
VoiceFlow Fine-tuning — RunPod (unsloth + NVIDIA)
Qwen2.5-7B-Instruct-bnb-4bit, LoRA rank=8, full dataset

Usage:
  python train_runpod.py

Output:
  /workspace/adapters/  — HuggingFace PEFT adapter
"""

import json
import os
from datasets import Dataset
from unsloth import FastLanguageModel
from trl import SFTTrainer, SFTConfig

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MODEL_NAME   = "unsloth/Qwen2.5-7B-Instruct-bnb-4bit"
MAX_SEQ_LEN  = 512
LORA_RANK    = 8
LORA_ALPHA   = 16
BATCH_SIZE   = 2
GRAD_ACCUM   = 4          # effective batch = 8
LR           = 1e-5
MAX_STEPS    = -1          # -1 = full epoch
NUM_EPOCHS   = 1
OUTPUT_DIR   = "/workspace/adapters"
TRAIN_FILE   = "/workspace/train.jsonl"
VALID_FILE   = "/workspace/valid.jsonl"

# ---------------------------------------------------------------------------
# Load model
# ---------------------------------------------------------------------------
print("Loading model...")
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=MODEL_NAME,
    max_seq_length=MAX_SEQ_LEN,
    dtype=None,
    load_in_4bit=True,
)

model = FastLanguageModel.get_peft_model(
    model,
    r=LORA_RANK,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"],
    lora_alpha=LORA_ALPHA,
    lora_dropout=0.0,
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=42,
)

# ---------------------------------------------------------------------------
# Load dataset
# ---------------------------------------------------------------------------
def load_jsonl(path):
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records

print("Loading datasets...")
train_records = load_jsonl(TRAIN_FILE)
valid_records = load_jsonl(VALID_FILE)

print(f"  Train: {len(train_records):,}")
print(f"  Valid: {len(valid_records):,}")

train_dataset = Dataset.from_list(train_records)
valid_dataset = Dataset.from_list(valid_records)

# ---------------------------------------------------------------------------
# Trainer
# ---------------------------------------------------------------------------
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=train_dataset,
    eval_dataset=valid_dataset,
    args=SFTConfig(
        dataset_text_field="text",
        max_seq_length=MAX_SEQ_LEN,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRAD_ACCUM,
        num_train_epochs=NUM_EPOCHS,
        max_steps=MAX_STEPS,
        learning_rate=LR,
        fp16=False,
        bf16=True,
        logging_steps=50,
        eval_strategy="steps",
        eval_steps=500,
        save_strategy="steps",
        save_steps=500,
        output_dir=OUTPUT_DIR,
        report_to="none",
        warmup_steps=100,
    ),
)

print("Starting training...")
trainer.train()

# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------
print(f"Saving adapter to {OUTPUT_DIR}...")
model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)
print("Done!")
