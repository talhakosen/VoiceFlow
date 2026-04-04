"""
VoiceFlow Qwen v2 Fine-tuning — filler/disfluency temizleme
Mevcut adapter bilgisi korunur (mixed dataset: 496 filler + 600 existing)
RunPod H100 veya RTX 4090

Usage:
  python train_runpod_v2.py

SCP öncesi:
  scp -P <PORT> ml/qwen/datasets/v2/train.jsonl root@<IP>:/workspace/train_v2.jsonl
  scp -P <PORT> ml/qwen/datasets/v2/valid.jsonl root@<IP>:/workspace/valid_v2.jsonl
  scp -P <PORT> ml/qwen/scripts/train_runpod_v2.py root@<IP>:/workspace/

Output: /workspace/adapters_v2/
"""

from datasets import Dataset
from unsloth import FastLanguageModel
from trl import SFTTrainer, SFTConfig

MODEL_NAME  = "unsloth/Qwen2.5-7B-Instruct-bnb-4bit"
MAX_SEQ_LEN = 512
LORA_RANK   = 8
LORA_ALPHA  = 16
BATCH_SIZE  = 8
GRAD_ACCUM  = 2          # effective batch = 16
LR          = 8e-6       # v1'den biraz düşük — catastrophic forgetting azalt
NUM_EPOCHS  = 3          # küçük dataset, 3 epoch yeterli (~930 * 3 = 2790 step / eff_batch 16 = ~174 iter)
MAX_STEPS   = 500        # ~15 dk H100, ~30 dk 4090 — erken dur
OUTPUT_DIR  = "/workspace/adapters_v2"
TRAIN_FILE  = "/workspace/train_v2.jsonl"
VALID_FILE  = "/workspace/valid_v2.jsonl"

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

def load_jsonl(path):
    import json
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return Dataset.from_list(rows)

print("Loading datasets...")
train_ds = load_jsonl(TRAIN_FILE)
valid_ds = load_jsonl(VALID_FILE)
print(f"  train: {len(train_ds)}, valid: {len(valid_ds)}")

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=train_ds,
    eval_dataset=valid_ds,
    args=SFTConfig(
        dataset_text_field="text",
        max_seq_length=MAX_SEQ_LEN,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRAD_ACCUM,
        warmup_steps=20,
        max_steps=MAX_STEPS,
        num_train_epochs=NUM_EPOCHS,
        learning_rate=LR,
        fp16=False,
        bf16=True,
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=50,
        save_strategy="steps",
        save_steps=100,
        output_dir=OUTPUT_DIR,
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="cosine",
        seed=42,
        report_to="none",
    ),
)

print("Training...")
trainer.train()

print("Saving adapter...")
model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)
print(f"Done → {OUTPUT_DIR}")
print()
print("Sonraki adım (Mac'te):")
print(f"  scp -rP <PORT> root@<IP>:{OUTPUT_DIR} ./ml/qwen/adapters_v2_runpod")
print("  python ml/qwen/scripts/convert_adapter.py --input ml/qwen/adapters_v2_runpod --output ml/qwen/adapters_v2_mlx")
