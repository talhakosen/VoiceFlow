#!/bin/bash
# VoiceFlow — Whisper Stage 2 (Noktalama) Training Setup
# Pod: voiceflow-whisper-stage2 (H100 80GB)
#
# Önce Mac'ten yükle:
#   scp -P <PORT> ml/whisper/whisper_stage2_finetune.py root@<IP>:/workspace/
#   scp -P <PORT> ml/whisper/datasets/issai/issai_punctuated.jsonl root@<IP>:/workspace/
#
# Sonra: export HF_TOKEN=hf_xxx && bash /workspace/stage2.sh
#
# Süre: ~5 dakika setup + ~2 saat training

set -e

echo "=== VoiceFlow Whisper Stage 2 Setup ==="
echo "GPU: $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo 'N/A')"
echo "RAM: $(free -h | awk '/^Mem:/{print $2}')"
echo "HF_TOKEN: ${HF_TOKEN:0:10}..."
echo ""

# 1. Script + data kontrol
if [ ! -f /workspace/whisper_stage2_finetune.py ]; then
  echo "[HATA] whisper_stage2_finetune.py bulunamadı!"
  echo "Mac'ten yükle: scp -P <PORT> ml/whisper/whisper_stage2_finetune.py root@<IP>:/workspace/"
  exit 1
fi

if [ ! -f /workspace/issai_punctuated.jsonl ]; then
  echo "[HATA] issai_punctuated.jsonl bulunamadı!"
  echo "Mac'ten yükle: scp -P <PORT> ml/whisper/datasets/issai/issai_punctuated.jsonl root@<IP>:/workspace/"
  exit 1
fi

echo "[OK] Script ve JSONL mevcut."
wc -l /workspace/issai_punctuated.jsonl

# 2. Pip paketleri
echo ""
echo "[1/3] Pip kurulum (bitsandbytes dahil)..."
pip install \
  'transformers==4.44.2' \
  'peft==0.12.0' \
  soundfile \
  librosa \
  accelerate \
  bitsandbytes \
  huggingface_hub \
  -q

echo "Pip tamamlandı."

# 3. ISSAI WAV konumu
echo ""
echo "[2/3] ISSAI WAV kontrol..."

ISSAI_VOLUME="/workspace/issai/extracted"
ISSAI_ROOT="/root/issai/extracted"
ISSAI_RAMDIR="/dev/shm/issai/extracted"

if [ -d "$ISSAI_VOLUME" ] && find "$ISSAI_VOLUME" -name "*.wav" -quit 2>/dev/null; then
  echo "ISSAI bulundu: $ISSAI_VOLUME (volume — kalıcı)"
  ISSAI_SOURCE="$ISSAI_VOLUME"
elif [ -d "$ISSAI_ROOT" ] && find "$ISSAI_ROOT" -name "*.wav" -quit 2>/dev/null; then
  echo "ISSAI bulundu: $ISSAI_ROOT (container — bu session)"
  ISSAI_SOURCE="$ISSAI_ROOT"
else
  echo "ISSAI bulunamadı — HF'ten indiriliyor (~20GB)..."
  mkdir -p /workspace/issai
  python3 - <<EOF
import os
from huggingface_hub import hf_hub_download
hf_hub_download(
    repo_id="issai/Turkish_Speech_Corpus",
    filename="ISSAI_TSC_218.tar.gz",
    repo_type="dataset",
    local_dir="/workspace/issai",
    token=os.environ.get("HF_TOKEN"),
)
EOF
  echo "Çıkartılıyor..."
  mkdir -p /workspace/issai/extracted
  tar -xzf /workspace/issai/ISSAI_TSC_218.tar.gz -C /workspace/issai/extracted
  echo "ISSAI hazır: /workspace/issai/extracted"
  ISSAI_SOURCE="/workspace/issai/extracted"
fi

# 4. RAM disk trick (I/O darboğazını kaldır)
echo ""
RAM_GB=$(free -g | awk '/^Mem:/{print $7}')
ISSAI_SIZE_GB=$(du -sg "$ISSAI_SOURCE" 2>/dev/null | awk '{print $1}' || echo 0)

echo "Kullanılabilir RAM: ${RAM_GB}GB | ISSAI boyutu: ~${ISSAI_SIZE_GB}GB"

if [ "$RAM_GB" -gt "$((ISSAI_SIZE_GB + 20))" ]; then
  echo "RAM yeterli → RAM disk'e kopyalanıyor (/dev/shm/issai)..."
  mkdir -p /dev/shm/issai
  cp -r "$ISSAI_SOURCE" /dev/shm/issai/
  echo "RAM disk hazır: /dev/shm/issai/extracted"
  echo "(Script otomatik /dev/shm/issai/extracted'ı kullanacak)"
else
  echo "RAM yetersiz → doğrudan diskten okuyacak (yavaş olabilir)"
fi

# 5. Training başlat
echo ""
echo "[3/3] Stage 2 training başlatılıyor..."
cd /workspace
nohup python whisper_stage2_finetune.py > /workspace/stage2.log 2>&1 &
TRAIN_PID=$!

echo ""
echo "=== Stage 2 Training Başladı ==="
echo "PID    : $TRAIN_PID"
echo "Log    : tail -f /workspace/stage2.log"
echo "Çıktı  : /workspace/voiceflow-whisper-tr-v2"
echo ""
echo "Beklenen süre: ~2 saat (batch=32, torch.compile, RAM disk)"
echo ""
echo "Bittikten sonra Mac'e al:"
echo "  scp -rP <PORT> root@<IP>:/workspace/voiceflow-whisper-tr-v2 ./ml/whisper/models/"
