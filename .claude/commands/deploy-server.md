---
description: Build Docker image and deploy to RunPod or on-premise server
---

# Deploy VoiceFlow Server: $ARGUMENTS

> **Phase 5 feature** — Docker + RunPod deployment is deferred. Do not run this until Phase 5 is active.
> Current focus: Phase 2 (Context Engine). See `.claude/develop-plan.md`.

Deploy the backend to server mode (RunPod or on-premise).

## Pre-flight Checks

1. `docker compose config` — verify compose file parses
2. Check `BACKEND_MODE=server` is set in environment
3. Verify `API_KEYS` env var is set (not empty)
4. Confirm GPU availability: `nvidia-smi` on target server
5. Verify RecordingService starts cleanly: `docker compose logs voiceflow-api`

## Local Docker Test

```bash
cd backend
docker compose build
docker compose up -d
sleep 10
curl http://localhost:8765/health
```

Expected: `{"status":"healthy","model_loaded":true,"llm_loaded":false}`

## RunPod Deploy

1. Push image to registry (if using custom image)
2. Create/update pod: RTX 4090, 24GB VRAM, Community Cloud
3. Attach persistent network volume (model cache — avoid re-download on restart)
4. Set env vars: `BACKEND_MODE=server`, `API_KEYS`, `LLM_MODEL=qwen2.5:7b`, `WHISPER_MODEL=large-v3`
5. Verify health endpoint accessible

## Performance Verification

After deploy, test all three modes:
```bash
# Start recording
curl -X POST http://SERVER:8765/api/start -H "X-Api-Key: $KEY"
# Stop + transcribe (no LLM)
time curl -X POST http://SERVER:8765/api/stop -H "X-Api-Key: $KEY"
# Enable correction + test each mode
curl -X POST http://SERVER:8765/api/config \
  -H "X-Api-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"correction_enabled": true, "mode": "engineering"}'
```

**Target: <2 seconds total**

If >2s:
- Check if models are loaded (not cold start) — `/health` shows `model_loaded`, `llm_loaded`
- Check GPU utilization: `nvidia-smi dmon` during request
- Check timing in logs: `/tmp/voiceflow.log` has Whisper ms + LLM ms breakdown

## On-Premise Deploy

```bash
# On customer server
git clone [repo]
cp .env.example .env  # Fill: API_KEYS, BACKEND_MODE=server
docker compose -f docker-compose.server.yml up -d
```

Verify with customer IT:
- Server only accessible via company VPN
- Port 8765 not exposed to public internet
- Network volume mounted for model cache
- `X-Api-Key` per user configured
