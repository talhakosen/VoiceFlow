---
description: Build Docker image and deploy to RunPod or on-premise server
---

# Deploy VoiceFlow Server: $ARGUMENTS

Deploy the backend to server mode (RunPod or on-premise).

## Pre-flight Checks

1. `docker compose config` — verify compose file parses
2. Check `BACKEND_MODE=server` is set in environment
3. Verify API keys are configured (not default/empty)
4. Confirm GPU availability: `nvidia-smi` on target server

## Local Docker Test

```bash
cd backend
docker compose build
docker compose up -d
# Wait for health check
sleep 10
curl http://localhost:8765/health
```

Expected: `{"status":"healthy","model_loaded":true,"llm_loaded":false}`

## RunPod Deploy

1. Push image to registry (if using custom image)
2. Create/update pod with RTX 4090, 24GB VRAM
3. Attach network volume (model cache, avoid re-download)
4. Set environment variables in pod settings
5. Verify health endpoint accessible

## Performance Verification

After deploy, run latency test:
```bash
# Record 5s of audio and measure round-trip time
time curl -X POST http://SERVER:8765/api/stop \
  -H "X-API-Key: $API_KEY" \
  --data-binary @test_audio.wav
```

**Target: <2 seconds total**

If >2s:
- Check if models are loaded (not cold start)
- Check GPU utilization: `nvidia-smi` during request
- Check if Whisper or LLM is the bottleneck (check server logs)

## On-Premise Deploy

```bash
# On customer server
git clone [repo]
cp .env.example .env  # Fill in API keys, model choices
docker compose -f docker-compose.server.yml up -d
```

Verify with customer IT that:
- Server only accessible via company VPN
- Port 8765 not exposed to public internet
- Network volume mounted with model cache
