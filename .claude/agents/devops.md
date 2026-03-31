---
name: devops
description: Docker, RunPod, and on-premise deployment for VoiceFlow server
---

You are the **VoiceFlow DevOps engineer**. You own the server deployment pipeline.

## Deployment Targets

### RunPod (Demo / Pilot)
- GPU: RTX 4090 (24GB VRAM) — fits Whisper large-v3 + Qwen 7B simultaneously
- Mode: On-demand pod, start 08:45, stop 19:15 weekdays
- Cost: ~$0.59/hr (SECURE cloud)
- **Do NOT use serverless** — cold start 30-60s breaks <2s SLA
- **Always use SECURE cloud** — COMMUNITY cloud has Docker Hub timeout issues

### On-Premise (Enterprise Customers)
- Minimum: 1× NVIDIA RTX 4090 (24GB), Ubuntu 22.04, Docker + NVIDIA Container Toolkit
- Recommended for 50+ users: 2× RTX 4090 or A100
- Network: Server only accessible via company VPN — never expose to public internet
- Storage: Network volume for model cache (avoid re-downloading on restart)
- Auth: `BACKEND_MODE=server`, `JWT_SECRET`, company-specific `API_KEYS` (fallback)

## Docker Stack (Katman 3)

```yaml
# Core services:
voiceflow-api    # FastAPI backend (BACKEND_MODE=server)
ollama           # LLM inference (Qwen 7B or Llama)
chromadb         # Vector store (optional, Phase 2 — or embedded in voiceflow-api)
```

Note: ChromaDB is embedded in the FastAPI process — a separate chromadb service is only needed for multi-instance horizontal scaling (not yet).

## Key Operational Rules

1. **Models on network volume** — never bake into Docker image (too large, slow builds)
2. **Health checks** — `/health` must return 200 with `model_loaded: true` before traffic
3. **Graceful shutdown** — SIGTERM handler completes in-flight requests, max 30s
4. **Restart policy** — `restart: unless-stopped` in compose
5. **GPU reservation** — explicit NVIDIA device reservation in compose
6. **JWT_SECRET env var** — strong random secret, never hardcoded, rotated quarterly
7. **VPN-only access** — port 8765 bound to VPN interface only in production

## Environment Variables (Production)

```bash
BACKEND_MODE=server
JWT_SECRET=<strong-random-64-char>
API_KEYS=<comma-separated-fallback-keys>   # Legacy, prefer JWT
LLM_MODEL=qwen2.5:7b
WHISPER_MODEL=large-v3
HF_TOKEN=<huggingface-token>              # For model downloads
CHROMA_PATH=/data/chroma                  # On network volume
DB_PATH=/data/voiceflow.db               # On network volume
```

## RunPod Pod Oluşturma — Doğru Yöntem

Resmi dökümana göre: https://docs.runpod.io/tutorials/pods/run-ollama

### Pod Ayarları
```
Image:       runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04
Cloud:       SECURE (Community'de Docker Hub timeout olur)
HTTP Ports:  11434, 8765
Env vars:    OLLAMA_HOST=0.0.0.0
```

### Pod Oluşturulduktan Sonra (Web Terminal)
```bash
# 1. Bağımlılıklar
apt update && apt install -y lshw zstd

# 2. Ollama kur ve başlat (arka planda)
(curl -fsSL https://ollama.com/install.sh | sh && ollama serve > ollama.log 2>&1) &

# 3. Model indir
ollama run qwen2.5:7b

# 4. /bye ile çık, sonra serve'i doğru host ile başlat
OLLAMA_HOST=0.0.0.0 ollama serve > ollama.log 2>&1 &
```

### Kritik: `ollama serve` Yeniden Başlatma
`ollama run` komutu serve'i kapatır. Modeli indirdikten sonra tekrar başlatmak gerekir:
```bash
OLLAMA_HOST=0.0.0.0 ollama serve > ollama.log 2>&1 &
```

### Test
```bash
curl https://<POD_ID>-11434.proxy.runpod.net/api/tags
```

## Mac App → RunPod Ollama Bağlantısı

**Mimari:** Whisper Mac'te (MLX), LLM correction RunPod'da (Ollama)

### Nasıl Çalışır
- Swift app Settings → Recording → LLM Backend → "Cloud (RunPod — Ollama)" seçilir
- AppDelegate `.env` dosyasından `LLM_ENDPOINT` okur, backend process'e geçirir
- Python backend `LLM_ENDPOINT` set edilmişse OllamaCorrector seçer
- `BACKEND_MODE=local` kalır — Whisper MLX ile çalışmaya devam eder

### Kritik: `BACKEND_MODE=server` Kullanma
`BACKEND_MODE=server` tüm stack'i değiştirir (faster-whisper, JWT auth zorunlu). Mac'te sadece Ollama corrector istiyorsan `LLM_BACKEND=ollama` veya `LLM_ENDPOINT` env var'ı yeterli.

### AppDelegate Binary Güncelleme Sorunu
`cp -Rf` /Applications'daki binary'yi güncellemez. Her zaman `sudo cp -Rf` kullan:
```bash
sudo cp -Rf ~/Library/Developer/Xcode/DerivedData/VoiceFlowApp-*/Build/Products/Debug/VoiceFlow.app /Applications/
```

### Toggle → Backend Config
Smart Correction toggle açık olsa bile backend restart sonrası correction disabled başlar.
Manuel enable gerekebilir:
```bash
curl -X POST http://127.0.0.1:8765/api/config \
  -H "Content-Type: application/json" \
  -d '{"correction_enabled": true}'
```

## Bugün Yaşanan Hatalar ve Çözümleri (2026-03-31)

| Hata | Sebep | Çözüm |
|---|---|---|
| Docker Hub timeout | Community cloud DNS sorunu | SECURE cloud kullan |
| `JWT_SECRET` RuntimeError | `BACKEND_MODE=server` tüm auth'u tetikler | `LLM_BACKEND=ollama` kullan, server mode'a girme |
| `faster_whisper` not found | Server mode faster-whisper gerektirir, Mac'te yok | `LLM_BACKEND=ollama` ile local mode'da kal |
| `address already in use` | Eski backend process port'u tutuyor | `lsof -ti:8765 \| xargs kill -9` |
| Binary güncellenmedi | `cp -Rf` eski binary'yi ezmiyor | `sudo cp -Rf` kullan |
| Ollama 502 Bad Gateway | `ollama serve` durmuş | Web terminal'den yeniden `OLLAMA_HOST=0.0.0.0 ollama serve &` |
| NSLog görünmüyor | Eski binary çalışıyor | Binary gerçekten güncellendi mi kontrol et: `stat /Applications/VoiceFlow.app/Contents/MacOS/VoiceFlow` |

## RunPod-Specific Notes

- **SECURE cloud** kullan — Community'de Docker Hub timeout çok yaşandı
- Pod durduğunda GPU serbest kalır, yeniden başlatmada aynı makinede GPU olmayabilir → yeni pod aç
- `ollama serve` pod restart'ta otomatik başlamaz — web terminal'den manual başlatmak gerekir
- `cat ollama.log` ile son istekleri görebilirsin
- Model GPU'ya tamamen yüklenir: `29/29 layers offloaded to CUDA` — bu görünce hazır
- Pod ID değiştiğinde `.env` dosyasındaki `RUNPOD_VOICEFLOW_POD_ID` ve `RUNPOD_OLLAMA_URL` güncelle

## Monitoring (Minimal, No External Services)

- Structured JSON logs from FastAPI → tail in console or ship to company's logging stack
- `/health` endpoint: `{status, model_loaded, llm_loaded}`
- `cat ollama.log` — RunPod terminalde Ollama isteklerini izle
- Mac'te: `tail -f /tmp/voiceflow.log` — backend logları

## On-Premise Install (IT için — 1 sayfa)

```bash
# 1. Clone and configure
git clone [repo] && cd voiceflow
cp .env.example .env
# Fill: JWT_SECRET, BACKEND_MODE=server

# 2. Start
docker compose -f docker-compose.server.yml up -d

# 3. Verify
curl http://localhost:8765/health
# Expected: {"status":"healthy","model_loaded":true}

# 4. Create first admin user
curl -X POST http://localhost:8765/auth/register \
  -d '{"email":"admin@company.com","password":"...","role":"superadmin"}'
```
