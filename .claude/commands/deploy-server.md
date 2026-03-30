---
description: Build Docker image and deploy to RunPod or on-premise server
---

# Deploy VoiceFlow Server: $ARGUMENTS

> **Katman 3 feature** — Docker + RunPod deployment is deferred. Do not run until Katman 3 is active.
> Current focus: Katman 1 (UI/UX + Dictionary + Snippets). See `.claude/develop-plan.md`.

Deploy the backend to server mode (RunPod or on-premise).

## Pre-flight Checks

1. `docker compose config` — verify compose file parses
2. Check `BACKEND_MODE=server` in environment
3. Verify `JWT_SECRET` env var is set (Katman 2+ required)
4. Verify `API_KEYS` env var (legacy fallback)
5. Confirm GPU: `nvidia-smi` on target server
6. Verify RecordingService starts: `docker compose logs voiceflow-api`

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
2. Create pod: RTX 4090, 24GB VRAM, Community Cloud
3. Attach persistent network volume (model cache)
4. Set env vars: `BACKEND_MODE=server`, `JWT_SECRET`, `LLM_MODEL=qwen2.5:7b`, `WHISPER_MODEL=large-v3`
5. Verify health endpoint accessible
6. Create first admin user via `/auth/register`

## Performance Verification

```bash
# Login
TOKEN=$(curl -s -X POST http://SERVER:8765/auth/login \
  -d '{"email":"admin@co.com","password":"..."}' | jq -r .access_token)

# Start + stop recording (no LLM)
curl -X POST http://SERVER:8765/api/start -H "Authorization: Bearer $TOKEN"
time curl -X POST http://SERVER:8765/api/stop -H "Authorization: Bearer $TOKEN"
```

**Target: <2 seconds total**

If >2s:
- Check `/health` for `model_loaded`, `llm_loaded`
- Check GPU: `nvidia-smi dmon` during request
- Check logs for Whisper ms + LLM ms breakdown

## On-Premise Deploy (IT için)

```bash
git clone [repo] && cd voiceflow
cp .env.example .env
# Fill: JWT_SECRET, BACKEND_MODE=server

docker compose -f docker-compose.server.yml up -d
curl http://localhost:8765/health

# Create first admin
curl -X POST http://localhost:8765/auth/register \
  -d '{"email":"admin@company.com","password":"...","role":"superadmin"}'
```

Müşteri IT'sine kontrol listesi:
- [ ] Port 8765 sadece VPN arayüzünde açık
- [ ] JWT_SECRET güçlü ve rastgele
- [ ] Network volume model cache'e bağlı
- [ ] Backup: SQLite ve ChromaDB dizinleri
