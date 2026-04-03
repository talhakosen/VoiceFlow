# VoiceFlow — Qwen Fine-Tuning (ASR Correction)

Qwen2.5-7B'yi Türkçe ASR düzeltme için fine-tune eder.

## Klasör Yapısı

```
ml/qwen/
├── scripts/
│   ├── train_runpod.py        ← RunPod NVIDIA training (unsloth)
│   ├── prepare_dataset.py     ← veri kaynaklarını birleştir → datasets/
│   ├── convert_adapter.py     ← HF PEFT → MLX format dönüşümü
│   ├── evaluate.py            ← WER/CER/exact-match raporu
│   └── lora_config.yaml       ← MLX local training config
├── datasets/
│   ├── train.jsonl            ← 244K pair (Qwen chat format)
│   ├── valid.jsonl            ← 30K pair
│   └── test.jsonl             ← 30K pair
└── adapters_mlx/              ← Production adapter (canlıda, .env ile yüklenir)
```

## 1. Dataset Hazırla

```bash
cd ml/qwen/scripts
python prepare_dataset.py \
    --sources ../../data_gen/datasets/qwen/corruption_pairs.jsonl \
              ../../data_gen/datasets/qwen/asr_training_data.jsonl \
              ../../data_gen/datasets/qwen/gecturk_pairs.jsonl \
              ../../data_gen/datasets/qwen/oneri_pairs.jsonl \
              ../../data_gen/datasets/qwen/word_order_pairs.jsonl \
    --output-dir ../datasets/
```

## 2a. MLX ile Local Training (Mac)

```bash
cd ml/qwen/scripts
mlx_lm.lora --config lora_config.yaml
```

## 2b. RunPod ile Cloud Training (NVIDIA)

```bash
# RunPod'a kopyala ve çalıştır
python train_runpod.py
# Adapter çıktısı: /workspace/adapters/ (HF PEFT format)
```

## 3. HF Adapter → MLX Format Dönüşümü (RunPod sonrası)

```bash
cd ml/qwen/scripts
python convert_adapter.py
# Çıktı: ../adapters_mlx/
```

## 4. Değerlendirme

```bash
cd ml/qwen/scripts
python evaluate.py --combined eval_results.jsonl --output report.json
```

## 5. Aktif Etme

`.env` dosyasında:
```bash
LLM_ADAPTER_PATH=../ml/qwen/adapters_mlx
```
