#!/bin/bash
# VoiceFlow — ISSAI Whisper Training Setup
# Pod: voiceflow-whisper-issai (H100 80GB)
# Çalıştır: bash setup/issai.sh  (veya pod başladıktan sonra SSH ile)
#
# Gereklilik: HF_TOKEN env var set edilmiş olmalı
#   export HF_TOKEN=hf_xxx
#
# Beklenen süre: pip install ~5 dakika, training ~4-5 saat

set -e

echo "=== VoiceFlow ISSAI Setup ==="
echo "GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null || echo 'N/A')"
echo "HF_TOKEN: ${HF_TOKEN:0:10}..."
echo ""

# 1. Pip paketleri
echo "[1/3] Pip kurulum..."
pip install \
  'transformers==4.44.2' \
  'peft==0.12.0' \
  datasets \
  soundfile \
  librosa \
  evaluate \
  accelerate \
  huggingface_hub \
  -q

echo "Pip tamamlandı."

# 2. Training script'i kopyala (Mac'ten SCP bekleniyor)
#    Mac'ten çalıştır: scp -P <PORT> ml/whisper/whisper_issai_finetune.py root@<IP>:/workspace/
if [ ! -f /workspace/whisper_issai_finetune.py ]; then
  echo ""
  echo "[UYARI] /workspace/whisper_issai_finetune.py bulunamadı!"
  echo "Mac'ten yükle: scp -P <PORT> ml/whisper/whisper_issai_finetune.py root@<IP>:/workspace/"
  echo "Sonra tekrar çalıştır: cd /workspace && nohup python whisper_issai_finetune.py > training.log 2>&1 &"
  exit 1
fi

# 3. Training başlat
echo ""
echo "[3/3] Training başlatılıyor (nohup + background)..."
cd /workspace
nohup python whisper_issai_finetune.py > /workspace/training.log 2>&1 &
TRAIN_PID=$!

echo ""
echo "=== Training Başladı ==="
echo "PID: $TRAIN_PID"
echo "Log: tail -f /workspace/training.log"
echo ""
echo "Çıktı: /workspace/voiceflow-whisper-tr"
echo "SCP sonrası: scp -rP <PORT> root@<IP>:/workspace/voiceflow-whisper-tr ./ml/whisper/"
