"""
VoiceFlow Qwen v3 Fine-tuning — transformers + peft (unsloth-free)
CUDA 12.4 uyumlu (torch 2.x cu121/cu124)

v2 adapter ağırlıklarından başlar. Yoksa base model.
Dataset: ml/qwen/datasets/v3/ — 2155 pairs (v2 filler + new initial/complex/semantic/backtrack)

RunPod H100 80GB

SCP:
  scp -rP <PORT> ml/qwen/adapters/v2.0/raw root@<IP>:/workspace/adapters_v2
  scp -P <PORT> ml/qwen/datasets/v3/train.jsonl root@<IP>:/workspace/train_v3.jsonl
  scp -P <PORT> ml/qwen/datasets/v3/valid.jsonl root@<IP>:/workspace/valid_v3.jsonl
  scp -P <PORT> ml/qwen/scripts/train_hf.py root@<IP>:/workspace/

Output: /workspace/adapters_v3/
"""

import os
import json
import torch
from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments
from peft import LoraConfig, get_peft_model, PeftModel
from trl import SFTTrainer, SFTConfig

V2_ADAPTER_PATH = "/workspace/adapters_v2"
BASE_MODEL      = "Qwen/Qwen2.5-7B-Instruct"
MAX_SEQ_LEN     = 512
LORA_RANK       = 8
LORA_ALPHA      = 16
BATCH_SIZE      = 4
GRAD_ACCUM      = 4       # effective batch = 16
LR              = 5e-6
MAX_STEPS       = 800
OUTPUT_DIR      = "/workspace/adapters_v3"
TRAIN_FILE      = "/workspace/train_v3.jsonl"
VALID_FILE      = "/workspace/valid_v3.jsonl"

print(f"CUDA: {torch.cuda.is_available()}, device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A'}")

# Load model
if os.path.isdir(V2_ADAPTER_PATH) and os.path.exists(os.path.join(V2_ADAPTER_PATH, "adapter_config.json")):
    print(f"V2 adapter bulundu: {V2_ADAPTER_PATH}")
    base = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, torch_dtype=torch.bfloat16, device_map="auto"
    )
    model = PeftModel.from_pretrained(base, V2_ADAPTER_PATH, is_trainable=True)
    tokenizer = AutoTokenizer.from_pretrained(V2_ADAPTER_PATH)
    print("V2 adapter yüklendi — devam ediliyor")
else:
    print(f"V2 adapter yok — base model: {BASE_MODEL}")
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, torch_dtype=torch.bfloat16, device_map="auto"
    )
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    lora_cfg = LoraConfig(
        r=LORA_RANK, lora_alpha=LORA_ALPHA,
        target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"],
        lora_dropout=0.0, bias="none", task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_cfg)

model.enable_input_require_grads()
model.print_trainable_parameters()

def load_jsonl(path):
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return Dataset.from_list(rows)

print("Datasets yükleniyor...")
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
        gradient_checkpointing=True,
        warmup_steps=20,
        max_steps=MAX_STEPS,
        learning_rate=LR,
        bf16=True,
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=50,
        save_strategy="steps",
        save_steps=100,
        output_dir=OUTPUT_DIR,
        optim="adamw_torch",
        weight_decay=0.01,
        lr_scheduler_type="cosine",
        seed=42,
        report_to="none",
        dataloader_num_workers=0,
    ),
)

print("Training başlıyor...")
trainer.train()

print("Adapter kaydediliyor...")
model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)
print(f"Tamamlandı → {OUTPUT_DIR}")
print()
print("Sonraki adım (Mac'te):")
print(f"  scp -rP <PORT> root@<IP>:{OUTPUT_DIR} ./ml/qwen/adapters_v2_runpod")
print("  python ml/qwen/scripts/convert_adapter.py --input ml/qwen/adapters_v2_runpod --output ml/qwen/adapters_v2_mlx")
