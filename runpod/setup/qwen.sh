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
for f in /workspace/train.jsonl /workspace/valid.jsonl /workspace/train_runpod.py; do
  if [ ! -f "$f" ]; then
    echo "  EKSIK: $f"
    MISSING=1
  else
    echo "  OK: $f ($(wc -l < $f) satır)"
  fi
done

if [ "$MISSING" = "1" ]; then
  echo ""
  echo "[UYARI] Eksik dosyalar var. Mac'ten yükle:"
  echo "  scp -P <PORT> ml/qwen/datasets/train.jsonl root@<IP>:/workspace/"
  echo "  scp -P <PORT> ml/qwen/datasets/valid.jsonl root@<IP>:/workspace/"
  echo "  scp -P <PORT> ml/qwen/scripts/train_runpod.py root@<IP>:/workspace/"
  exit 1
fi

# 3. Training başlat
echo ""
echo "[3/3] Training başlatılıyor..."
cd /workspace
nohup python train_runpod.py > /workspace/training.log 2>&1 &
TRAIN_PID=$!

echo ""
echo "=== Training Başladı ==="
echo "PID: $TRAIN_PID"
echo "Log: tail -f /workspace/training.log"
echo ""
echo "Çıktı: /workspace/adapters/"
echo "SCP sonrası: scp -rP <PORT> root@<IP>:/workspace/adapters ./ml/qwen/adapters_runpod"
echo "Dönüşüm: cd ml/qwen/scripts && python convert_adapter.py"
