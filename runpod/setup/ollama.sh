#!/bin/bash
# VoiceFlow — Ollama Inference Setup
# Pod: voiceflow-ollama (RTX 4090)
# Çalıştır: bash setup/ollama.sh  (pod başladıktan veya restart sonrası)
#
# Not: Pod restart sonrası Ollama binary silinmez ama process ölür → tekrar çalıştır

set -e

echo "=== VoiceFlow Ollama Setup ==="
echo "GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null || echo 'N/A')"
echo ""

# 1. Ollama kur (idempotent — zaten varsa skip)
if ! command -v ollama &> /dev/null; then
  echo "[1/2] Ollama kuruluyor..."
  curl -fsSL https://ollama.com/install.sh | sh
else
  echo "[1/2] Ollama zaten kurulu: $(ollama --version)"
fi

# 2. Serve başlat
echo "[2/2] Ollama serve başlatılıyor..."
OLLAMA_HOST=0.0.0.0 nohup ollama serve > /root/ollama.log 2>&1 &
OLLAMA_PID=$!

# Hazır olana kadar bekle
echo "Hazır bekleniyor..."
for i in $(seq 1 30); do
  if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "Ollama hazır."
    break
  fi
  sleep 1
done

# 3. Model çek
echo ""
echo "Model indiriliyor: qwen2.5:7b (~4.5GB)..."
ollama pull qwen2.5:7b

echo ""
echo "=== Ollama Hazır ==="
echo "PID: $OLLAMA_PID"
echo "Local test: curl http://localhost:11434/api/tags"
echo "Proxy URL: https://\$(cat /etc/hostname | tr -d '\n')-11434.proxy.runpod.net (RunPod UI'dan kontrol et)"
echo ""
echo ".env güncelle:"
echo "  RUNPOD_OLLAMA_URL=https://<POD_ID>-11434.proxy.runpod.net"
