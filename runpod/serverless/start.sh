#!/bin/bash
set -e

MODEL="${OLLAMA_MODEL:-qwen2.5:7b}"
WHISPER_MODEL="${WHISPER_MODEL:-Systran/faster-whisper-large-v3}"

echo "=== VoiceFlow Serverless Worker ==="
echo "Whisper model: $WHISPER_MODEL"
echo "LLM model: $MODEL"

# Start Ollama in background
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to be ready (max 60s)
echo "Waiting for Ollama..."
READY=0
for i in $(seq 1 60); do
    if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "Ollama ready (${i}s)"
        READY=1
        break
    fi
    sleep 1
done

if [ "$READY" -eq 0 ]; then
    echo "ERROR: Ollama failed to start within 60s"
    exit 1
fi

# Pull LLM model
echo "Pulling $MODEL..."
ollama pull "$MODEL"
echo "Model ready"

# Pre-warm: keep model in GPU memory
curl -sf http://localhost:11434/api/generate \
    -d "{\"model\": \"$MODEL\", \"keep_alive\": -1}" > /dev/null 2>&1 || true

# Start RunPod handler
echo "Starting RunPod handler..."
exec python3 /handler.py
