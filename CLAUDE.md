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
Docs: `docs/architecture/`, `docs/ml/`, `docs/deployment/`, `docs/enterprise/`, `docs/discussions/`

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
- SQLite: `voiceflow.db` (repo root) — `DB_PATH` ile configure edilir (`config.yaml`)
- ChromaDB: `~/.voiceflow/chroma/` (tenant=company_id)

## Critical Dev Notes

- **After ANY Swift build**: Accessibility izni sıfırlanır → System Settings → Privacy → Accessibility → VoiceFlow'u etkinleştir. Auto-paste sessizce çalışmaz.
- **Fn key**: Release eventi güvenilmez — double-tap toggle + Force Stop yedek. Asla sadece key-up'a güvenme.
- **7B minimum**: 1.5B/3B Türkçe'de hallüsinasyon yapıyor (doğrulandı). 7B altına inme.
- **Whisper fine-tune**: Correction için Whisper frozen + Qwen adapter (hâlâ geçerli). Engineering mode için Whisper'ı da fine-tune ediyoruz: ISSAI 164K pair → voiceflow-whisper-tr → IT kayıtlar → voiceflow-whisper-it. Detay: `docs/ml/two-adapter-architecture.md`.
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
- **RunPod fine-tuning GPU util**: batch=2 + default optimizer → %7 GPU (CPU darboğazı). Kullan: `batch=8, grad_accum=2, optim="adamw_8bit", packing=True, dataloader_pin_memory=True`. Detay: `docs/ml/runpod-finetuning.md`.
- **RunPod disk**: `/workspace` (volume, 20GB kota) ≠ container disk (120GB). `df -h` yanıltıcı (257TB gösterir). Büyük dosyaları `/root/`'a indir.
- **ISSAI/Whisper paralel shard**: Kısa ses dosyalarında `BatchedInferencePipeline` yavaş (7K/saat). 3 paralel process = %99 GPU, ~9 saat (tek process 26 saat). `large-v3 float16` = 3.5GB → 3 instance = 10.5GB, RTX 4090'a rahat sığar. `SHARD_INDEX=N SHARD_TOTAL=3 python process_issai.py`. Detay: `docs/ml/runpod-finetuning.md`.
- **RunPod Pod ID**: `.env`'deki `RUNPOD_VOICEFLOW_POD_ID` ve `RUNPOD_OLLAMA_URL` pod değişince güncelle.
- **Config ayrımı**: `config.yaml` (non-secret: DB_PATH, LLM_ADAPTER_PATH, BACKEND_MODE, WHISPER_MODEL vb.) + `.env` (sadece secrets: API key'ler, token'lar). `backend/.env` oluşturma — tüm config root'ta.
- **LoRA adapter (fine-tuned)**: `ml/qwen/adapters_mlx/` (39MB). `config.yaml`'da `llm.adapter_path: ml/qwen/adapters_mlx`. HF PEFT → MLX dönüşüm scripti: `ml/qwen/scripts/convert_adapter.py`.
- **ML scripts**: `ml/qwen/` (scripts/, generators/, data/, datasets/, adapters_mlx/) + `ml/whisper/` (finetune scripts, generators/, datasets/issai/, datasets/it_dataset/).
- **RunPod pod configs**: `runpod/pods/*.json` + `runpod/setup/*.sh`. Yeni pod: `cd runpod && python create_pod.py issai|qwen|ollama`.
- **Whisper fine-tune (ISSAI)**: `ml/whisper/whisper_issai_finetune.py` — whisper-large-v3-turbo, ISSAI 164K pair, H100, çıktı `/workspace/voiceflow-whisper-tr`. Bu CLAUDE.md'deki "Whisper eğitilmez" notunun istisnası — sadece correction LoRA değil, ASR modeli de fine-tune ediyoruz.
- **2. round Qwen training**: ISSAI pairs (`ml/whisper/datasets/issai/issai_pairs_all.jsonl`) + mevcut dataset (`ml/qwen/data/`) → `prepare_dataset.py` → RunPod Qwen training.
- **RunPod pod configs**: `runpod/pods/*.json` + `runpod/setup/*.sh`. Yeni pod: `cd runpod && python create_pod.py issai|qwen|ollama`.
