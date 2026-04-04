#!/bin/bash
# VoiceFlow — Qwen LoRA Training Setup
# Pod: voiceflow-qwen-training (RTX 4090 24GB)
# Çalıştır: bash setup/qwen.sh
#
# Gereklilik: dataset'ler /workspace/ altında olmalı
#   scp -P <PORT> ml/qwen/datasets/train.jsonl root@<IP>:/workspace/
#   scp -P <PORT> ml/qwen/datasets/valid.jsonl root@<IP>:/workspace/
#   scp -P <PORT> ml/qwen/scripts/train_runpod.py root@<IP>:/workspace/
#
# Beklenen süre: unsloth kurulum ~15 dakika, training ~7 saat

set -e

echo "=== VoiceFlow Qwen Training Setup ==="
echo "GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null || echo 'N/A')"
echo "VRAM: $(nvidia-smi --query-gpu=memory.total --format=csv,noheader 2>/dev/null || echo 'N/A')"
echo ""

# 1. Unsloth + deps
echo "[1/3] Unsloth kurulum (~15 dakika, derleme gerekiyor)..."
pip install "unsloth[colab-new]@git+https://github.com/unslothai/unsloth.git" -q
pip install "unsloth_zoo" trl datasets -q

echo "Unsloth tamamlandı."

# 2. Dosya kontrolü
echo ""
echo "[2/3] Dosya kontrolü..."
MISSING=0

# v2 varsa onu kullan, yoksa v1'e bak
if [ -f /workspace/train_v2.jsonl ]; then
  TRAIN_FILE=/workspace/train_v2.jsonl
  VALID_FILE=/workspace/valid_v2.jsonl
  TRAIN_SCRIPT=/workspace/train_runpod_v2.py
  LOG_FILE=/workspace/training_v2.log
  echo "  Mod: v2 (filler dataset)"
else
  TRAIN_FILE=/workspace/train.jsonl
  VALID_FILE=/workspace/valid.jsonl
  TRAIN_SCRIPT=/workspace/train_runpod.py
  LOG_FILE=/workspace/training.log
  echo "  Mod: v1 (orijinal dataset)"
fi

for f in "$TRAIN_FILE" "$VALID_FILE" "$TRAIN_SCRIPT"; do
  if [ ! -f "$f" ]; then
    echo "  EKSIK: $f"
    MISSING=1
  else
    echo "  OK: $f ($(wc -l < $f) satır)"
  fi
done

if [ "$MISSING" = "1" ]; then
  echo ""
  echo "[UYARI] Eksik dosyalar var. Mac'ten yükle (v2):"
  echo "  scp -P <PORT> ml/qwen/datasets/v2/train.jsonl root@<IP>:/workspace/train_v2.jsonl"
  echo "  scp -P <PORT> ml/qwen/datasets/v2/valid.jsonl root@<IP>:/workspace/valid_v2.jsonl"
  echo "  scp -P <PORT> ml/qwen/scripts/train_runpod_v2.py root@<IP>:/workspace/"
  exit 1
fi

# 3. Training başlat
echo ""
echo "[3/3] Training başlatılıyor..."
cd /workspace
nohup python "$TRAIN_SCRIPT" > "$LOG_FILE" 2>&1 &
TRAIN_PID=$!

echo ""
echo "=== Training Başladı ==="
echo "PID: $TRAIN_PID"
echo "Log: tail -f $LOG_FILE"
echo ""
if [ "$TRAIN_SCRIPT" = "/workspace/train_runpod_v2.py" ]; then
  echo "Çıktı: /workspace/adapters_v2/"
  echo "SCP:   scp -rP <PORT> root@<IP>:/workspace/adapters_v2 ./ml/qwen/adapters_v2_runpod"
  echo "MLX:   python ml/qwen/scripts/convert_adapter.py --input ml/qwen/adapters_v2_runpod --output ml/qwen/adapters_v2_mlx"
  echo "Config: llm.adapter_path: ml/qwen/adapters_v2_mlx"
else
  echo "Çıktı: /workspace/adapters/"
  echo "SCP:   scp -rP <PORT> root@<IP>:/workspace/adapters ./ml/qwen/adapters_runpod"
  echo "MLX:   python ml/qwen/scripts/convert_adapter.py"
fi
