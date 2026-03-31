# VoiceFlow

Real-time speech-to-text for macOS — mlx-whisper + mlx-lm, enterprise on-premise.
**Hedef:** Türkiye'nin Wispr Flow'u — veri egemenliği, on-premise, kurumsal.

# IMPORTANT
ihtiyac halinde context7 ve sequentialthinking yapmayi unutma

## Quick Start

```bash
./voiceflow.sh start    # Start backend
./voiceflow.sh stop     # Stop backend
./voiceflow.sh restart  # Restart backend
./voiceflow.sh status   # Check status
```

### macOS App Build & Deploy (ALWAYS full clean build)
```bash
pkill -f "VoiceFlow.app" 2>/dev/null || true
rm -rf ~/Library/Developer/Xcode/DerivedData/VoiceFlowApp-*
xcodebuild -project VoiceFlowApp/VoiceFlowApp.xcodeproj -scheme VoiceFlowApp -configuration Debug clean build
rm -rf /Applications/VoiceFlow.app
cp -R ~/Library/Developer/Xcode/DerivedData/VoiceFlowApp-*/Build/Products/Debug/VoiceFlow.app /Applications/
open /Applications/VoiceFlow.app
```

## Katman Roadmap

| Katman | Versiyon | Odak |
|---|---|---|
| **1** | v0.3 | UI/UX (menu sadeleştirme + 2-panel Settings + pill overlay), Dictionary, Snippets |
| **2** | v0.4 | JWT auth, tenant izolasyon, admin web UI |
| **3** | v0.5+ | Style/ton, gamification, Docker, RunPod, DMG |

Detaylar: `.claude/develop-plan.md`

## Architecture (v0.2)

### Backend — Layered Architecture
```
api/routes.py          ← HTTP only: validate → Depends(get_service) → response
api/auth.py            ← API key middleware (Katman 2'de JWT'ye yükselecek)
services/recording.py  ← RecordingService: ALL pipeline logic (start/stop/transcribe/correct/save)
core/interfaces.py     ← AbstractTranscriber, AbstractCorrector, AbstractRetriever (ABCs)
transcription/         ← WhisperTranscriber (MLX) or FasterWhisperTranscriber (NVIDIA)
correction/            ← LLMCorrector (mlx-lm) or OllamaCorrector (httpx)
context/               ← ChromaRetriever (RAG, Phase 2)
db/storage.py          ← aiosqlite SQLite CRUD (~/.voiceflow/voiceflow.db)
```

### Swift — MVVM + Protocol DI
```
AppViewModel           ← @Observable @MainActor — ALL state + business logic
MenuBarController      ← NSMenu UI only (≤150 lines Katman 1 sonrası), observes AppViewModel
BackendService (actor) ← HTTP client, implements BackendServiceProtocol
AppDelegate            ← lifecycle only: creates AppViewModel, starts backend process
```

### Deployment Modes
- **Local** (`BACKEND_MODE=local`): MLX on Mac, 127.0.0.1, no auth
- **Local + Cloud LLM** (`LLM_BACKEND=ollama` + `LLM_ENDPOINT=...`): Whisper Mac'te, correction RunPod'da. `BACKEND_MODE=local` kalır!
- **Server** (`BACKEND_MODE=server`): NVIDIA GPU, 0.0.0.0, JWT auth zorunlu, faster-whisper gerektirir

## API

```
GET  /health                  → {status, model_loaded, llm_loaded}
GET  /api/status              → {status, is_recording}
POST /api/start               → start recording
POST /api/stop                → stop + transcribe + correct + save [X-User-ID header]
POST /api/force-stop          → always succeeds
POST /api/config              → {language?, task?, correction_enabled?, mode?, model?}
GET  /api/devices             → audio input devices
GET  /api/history             → SQLite history [?limit=&offset=&user_id=]
DELETE /api/history           → clear all history
POST /api/context/ingest      → index folder into ChromaDB (async)
GET  /api/context/status      → {count, is_ready, is_empty}
DELETE /api/context           → clear knowledge base
```

Modes: `general` | `engineering` | `office` — different LLM system prompts.

## Key Config

- Whisper (local): `mlx-community/whisper-small-mlx`
- LLM (local): `mlx-community/Qwen2.5-7B-Instruct-4bit` (~4GB)
- Embeddings (RAG): `all-MiniLM-L6-v2` (CPU, ~22MB, lazy loaded)
- Python venv: `backend/.venv` (python3.14)
- MLX executor: `ThreadPoolExecutor(max_workers=1)` in RecordingService — Metal GPU not thread-safe
- SQLite: `~/.voiceflow/voiceflow.db`
- ChromaDB: `~/.voiceflow/chroma/` (tenant=company_id)

## Critical Dev Notes

- **After ANY Swift build**: Accessibility izni sıfırlanır → System Settings → Privacy → Accessibility → VoiceFlow'u etkinleştir. Auto-paste sessizce çalışmaz.
- **Fn key**: Release eventi güvenilmez — double-tap toggle + Force Stop yedek. Asla sadece key-up'a güvenme.
- **7B minimum**: 1.5B/3B Türkçe'de hallüsinasyon yapıyor (doğrulandı). 7B altına inme.
- **faster-whisper**: numpy array değil BytesIO alır → `soundfile.write(buf, audio, sr, format="WAV")`.
- **MLX LLM on-demand**: Correction açılınca yükle, kapanınca unload (~4GB boşalt).
- **Mode capture**: `RecordingService.stop()`'ta `active_mode = corrector.config.mode` ilk önce yakala — concurrent `/api/config` race condition önler.
- **ChromaDB lazy**: `_build_retriever()` sadece `ChromaRetriever()` döner, `is_empty()` çağırma — MiniLM startup'ta indirilmez.
- **NSPanel pattern**: Settings, History, Knowledge Base hepsi NSPanel floating window. SwiftUI `Settings {}` scene selector debug'da güvenilmez.
- **DerivedData**: Her build öncesi sil yoksa eski binary çalışır.
- **Swift binary güncelleme**: `cp -Rf` /Applications'ı güncellemez — `sudo cp -Rf` zorunlu.
- **Docker yok (local)**: Katman 3'e ertelendi. Local geliştirmede Docker kullanma.
- **HF_TOKEN**: Model indirme hızı için gerekli — env var olarak ver.
- **venv bozulursa**: `cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev,context]"`
- **BACKEND_MODE=server kullanma (Mac'te)**: faster-whisper + JWT_SECRET zorunlu hale gelir. Mac'te sadece Ollama corrector istiyorsan `LLM_BACKEND=ollama` + `LLM_ENDPOINT` yeterli.
- **RunPod Ollama**: SECURE cloud kullan (Community'de Docker Hub timeout). Pod restart sonrası `OLLAMA_HOST=0.0.0.0 ollama serve > ollama.log 2>&1 &` tekrar çalıştır.
- **RunPod Pod ID**: `.env`'deki `RUNPOD_VOICEFLOW_POD_ID` ve `RUNPOD_OLLAMA_URL` pod değişince güncelle.
