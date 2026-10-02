# VoiceFlow

Real-time speech-to-text for macOS — mlx-whisper + mlx-lm, enterprise on-premise.
**Hedef:** Türkiye'nin Wispr Flow'u — veri egemenliği, on-premise, kurumsal.

**Resmi Logo:** `assets/voiceflow_icon_preview.png` — koyu arka plan üzerinde waveform bars. Web, app icon, toolbar, menu bar dahil her yerde bu kullanılır. Başka logo kullanma.

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

### Web — Marketing Landing Page (`web/`)
```
Next.js 14 + Tailwind + Framer Motion — statik marketing sitesi
src/app/page.tsx        ← 8 section orchestration
src/components/sections/ ← Hero, Stats, Speed, HowItWorks, Features, Security, Testimonials, CTA
src/components/ui/      ← Button, Card, Badge, GradientText, FadeUp, Container
src/lib/constants.ts    ← tüm copy/data burada (type-safe)
src/types/index.ts      ← NavLink, Feature, Stat, Testimonial vb.
```
- Çalıştır: `cd web && npm run dev` (port 3000)
- İçerik değişikliği → sadece `constants.ts` düzenle
- Pricing section henüz yok (`PricingTier` tipi hazır, section eklenmedi)
- Social linkler `#` placeholder — canlıya geçmeden güncelle

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
- **Local + Cloud GPU** (`whisper.backend: runpod`): Ses Mac'te kaydedilir, transkripsiyon+düzeltme RunPod'da. **7x hızlı** (~850ms vs ~6sn). `BACKEND_MODE=local` kalır!
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
- LLM (local): `mlx-community/Qwen3-4B-Instruct-2507-4bit` (~2.2GB, adapter'sız) — `config.yaml: llm.mlx_model`
- Embeddings (RAG): `all-MiniLM-L6-v2` (CPU, ~22MB, lazy loaded)
- Python venv: `backend/.venv` (python3.14)
- MLX executor: `ThreadPoolExecutor(max_workers=1)` in RecordingService — Metal GPU not thread-safe
- SQLite: `voiceflow.db` (repo root) — `DB_PATH` ile configure edilir (`config.yaml`)
- ChromaDB: `~/.voiceflow/chroma/` (tenant=company_id)

## Critical Dev Notes

- **After ANY Swift build**: Accessibility izni sıfırlanır → System Settings → Privacy → Accessibility → VoiceFlow'u etkinleştir. Auto-paste sessizce çalışmaz.
- **Fn key**: Release eventi güvenilmez — double-tap toggle + Force Stop yedek. Asla sadece key-up'a güvenme.
- **Sessiz kayıt (rms=0.0000)**: İki sebebi var, ikisi de hata vermeden boş ses döndürür — (1) macOS mikrofon izni yok (her rebuild imzayı değiştirdiği için sıfırlanır; `AppDelegate.requestMicrophonePermission()` artık açıkça istiyor, `tccutil reset Microphone com.voiceflow.app` ile sıfırlanır), (2) Bluetooth kulaklık susturulmuş/uykuda (Jabra Evolve2 boom kolu). Backend artık sebebi `notice` alanıyla UI'a söylüyor ve her kayıtta cihaz adını logluyor. Çözüm: Ayarlar > Kayıt > Mikrofon'dan cihazı sabitle — İSİMLE saklanır (index'ler cihaz takıldıkça kayıyor) ve backend her restart'ta ayarı unuttuğu için AppDelegate tekrar gönderir.
- **LLM seçimi (2026-10-01)**: Qwen3-4B, Qwen2.5-7B+v3 adapter'dan iyi (WER 0.32 vs 0.40, 1.7x hızlı, yarı bellek). "7B minimum" kuralı Qwen2.5 içindi. Kumru-2B, Ministral-8B, Qwen3-8B elendi. Detay: `docs/ml/llm-model-degerlendirme.md`.
- **Whisper fine-tune**: Correction için Whisper frozen + Qwen adapter (hâlâ geçerli). Engineering mode için Whisper'ı da fine-tune ediyoruz: ISSAI 164K pair → voiceflow-whisper-tr → IT kayıtlar → voiceflow-whisper-it. Detay: `docs/ml/two-adapter-architecture.md`.
- **faster-whisper**: numpy array değil BytesIO alır → `soundfile.write(buf, audio, sr, format="WAV")`.
- **MLX LLM on-demand**: Correction açılınca yükle, kapanınca unload (~2.5GB boşalt).
- **Sözlük cache'i**: `get_dictionary(include_smart=True)` 78K kayıt döndürüyor ve her diktede okunuyordu (285ms — metin aşamasının tamamı). `dictionary_storage` içinde süreç-içi cache var; sözlüğü değiştiren HER fonksiyon `invalidate_dictionary_cache()` çağırmalı (test bunu zorluyor). Dönen liste PAYLAŞILIR, kopyalama — 78K kaydı kopyalamak cache'i anlamsız kılar. Aho-Corasick automaton'ı `dictionary_version()`'a bağlı (eskiden kayıt sayısına bakıyordu → sayı sabit kalıp içerik değişince bayat kalıyordu). Startup'ta bundle auto-load'dan SONRA ısıtılır. Sonuç: metin aşaması 313ms → ~3ms.
- **Sözlük Türkçe kelime koruması (2026-10-01)**: Otomatik kayıtlar (bundle/smart) gerçek Türkçe kelimeyi ikame edemez — `core/turkish_words.py`, yazma noktası `load_bundle_entries` + `bulk_add_smart_entries`, açılışta `purge_turkish_word_entries()`. Sebep: bundle üreticisi kısa terime ek yapıştırıp ("di"+"ye" → `diye → DI'ye`), indeksleme identifier'ı çevirip (`ekran → Screen`) 336 diktenin 302'sini bozmuştu. Manuel kayıtlar korumasız (kullanıcı bilerek ekler). Kelime listesi: `ml/dictionary/build_turkish_wordlist.py` (ISSAI) + kök+ek kuralı + `turkish_words_extra.txt` (ISSAI haber dili; buton/panel gibi teknik Türkçe yok — gözlenen hatada buraya ekle). Bundle üreticisi aynı kontrolü + İngilizce kelime yanlış bölme kontrolünü (`login` → log'in, `/usr/share/dict/words`) uyguluyor; bundle'ı elle düzenleme, `generate_it_bundle.py` ile üret.
- **Dinamik Whisper penceresi**: Whisper girdiyi hep 30sn'ye pad'ler → 4sn dikte de 30sn'lik hesabı öder. `transcription/dynamic_window.py` pencereyi `ceil(süre)+3sn`'ye kısaltır (min 6, max 30) → M4'te **~3x** (1.5sn ses: 1908→389ms). İki zorunlu koruma: `without_timestamps=True` (yoksa seek döngüsü SONSUZA kilitleniyor, >3.5dk ölçüldü) + 2sn'den az marjda cümle tekrarı → `has_repeated_span()` yakalarsa 30sn ile retry. Kapatmak için `config.yaml → whisper.dynamic_window: false`.
- **CoreML/WhisperKit ELENDİ (2026-09-30, ölçüldü)**: Kısa diktede 2.5x yavaş (3.2sn ses: MLX 311ms, WhisperKit 765ms), aynı boyut (1.5 GB), ilk yükleme 933 sn. Sebep: dinamik pencere taşınamıyor — CoreML'de girdi şekli derleme anında sabitlenir, dönüştürücüde encoder penceresi seçeneği yok. Fine-tune'umuz CoreML'e sorunsuz geçiyor ve Türkçe doğruluğu koruyor (iOS'a geçilirse yol açık). Argmax'ın PSNR testi bizim checkpoint'te deterministik DEĞİL (9.3–138 arası savruluyor), ona bakarak karar verme. Detay + tekrar denemek için: `docs/ml/coreml-whisperkit-degerlendirme.md`.
- **Mode capture**: `RecordingService.stop()`'ta `active_mode = corrector.config.mode` ilk önce yakala — concurrent `/api/config` race condition önler.
- **ChromaDB lazy**: `_build_retriever()` sadece `ChromaRetriever()` döner, `is_empty()` çağırma — MiniLM startup'ta indirilmez.
- **NSPanel pattern**: Settings, History, Knowledge Base hepsi NSPanel floating window. SwiftUI `Settings {}` scene selector debug'da güvenilmez.
- **DerivedData**: Her build öncesi sil yoksa eski binary çalışır.
- **Backend path hardcoded değil**: `AppConstants.backendPathCandidates` + marker doğrulaması (`src/voiceflow/main.py`). Repo taşınırsa listeye ekle ya da `defaults write com.voiceflow.app backendPathOverride /yeni/path/backend`. Yanlış cwd → `Process.run()` sessizce fırlatır, backend hiç açılmaz.
- **Servis butonları süreci yönetir**: `.restartBackend`/`.hardReset` → `backendProcessClient` (BackendProcessManager.shared). Sadece `/api/force-stop` atmak yetmez — backend ölüyse HTTP'nin kurtaracağı bir şey yok.
- **Watchdog**: 5sn'de bir `/health`; ölürse en fazla 3 kez hızlı restart, sonra SUSMAZ — 60sn'de bir yavaş retry'a geçer (engel kalkarsa kendi toparlar). `/tmp/voiceflow.log` append, Swift tarafı `/tmp/voiceflow-swift.log`.
- **Port temizliği lsof'a GÜVENMEZ**: `lsof` bu makinede `/usr/sbin/lsof`'ta; kod `/usr/bin/lsof` çağırıyordu, `Process.run()` ENOENT fırlatıyor, `catch` boş dizi dönüyordu → "Port free" yalanı → SIGKILL aşaması hiç çalışmadı, takılı bir backend portu 16 gün tuttu (2026-09-24). Artık: lsof aday listesi + **nihai karar `bind()` denemesiyle** (`isPortFree`, uvicorn'un çarptığı şeyin aynısı). Takılı uvicorn SIGTERM'i yutabiliyor (graceful shutdown MLX executor'da asılı) → TERM→bekle→KILL yükseltmesi ZORUNLU. Port temizlenemezse spawn edilmez, kullanıcıya PID ile söylenir.
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
- **LoRA adapter (fine-tuned)**: şu an KAPALI — v3.0 Qwen2.5-7B içindi, Qwen3-4B'de çalışmaz. Yeni adapter Qwen3-4B tabanlı eğitilmeli (dolgu temizliği zayıf). `config.yaml: llm.adapter_path`. Sürüm geçmişi: `ml/qwen/CHANGELOG.md`. HF PEFT → MLX dönüşüm scripti: `ml/qwen/scripts/convert_adapter.py`.
- **ML scripts**: `ml/qwen/` (scripts/, generators/, data/, datasets/, adapters/) + `ml/whisper/` (scripts/, datasets/issai/, datasets/it_dataset/, models/).
- **Whisper fine-tune (ISSAI)**: `ml/whisper/scripts/train_stage1.py` — whisper-large-v3-turbo, ISSAI 164K pair, H100, çıktı `tkosen/voiceflow-whisper-tr` (HF). Stage 1 TAMAMLANDI.
- **Whisper Stage 2 TAMAMLANDI**: `tkosen/voiceflow-whisper-tr-v2` (HF, PyTorch kaynak) → `ml/whisper/models/v2.0/` (MLX, aktif — `config.yaml: whisper.model`). Dönüşüm: `ml/whisper/scripts/convert_whisper_mlx.py`. Eğitim: `ml/whisper/scripts/train_stage2.py`, 10644 step, 2 epoch, H100. Sürüm geçmişi: `ml/whisper/CHANGELOG.md`.
- **Whisper Stage 2 OOM fix (doğrulanan config)**: `batch=16` (32'den düşürüldü), `gradient_checkpointing=True`, `bf16_full_eval=True` ZORUNLU, `eval_accumulation_steps=4`, `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`. Checkpoint resume: `RESUME_CHECKPOINT=/path/to/checkpoint-N` env var. Bu kombinasyon olmadan H100'da OOM — 2 kez crashed, 3. denemede stabil.
- **RunPod UI GPU% yanıltıcı**: CUDA compute workload'da UI'daki "GPU %" sütunu 0 gösterir (render engine ölçer). Gerçek kullanım için `nvidia-smi` veya VRAM%'e bak.
- **issai_pairs_clean.jsonl alan farkı**: `input` = Whisper ASR çıktısı (Qwen için), `output` = ground truth TXT (Whisper eğitimi için). Karıştırma!
- **ISSAI extraction zorunluluğu**: `/workspace` (NFS) = 1K WAV/dk (~167 dk). `/root/` (container SSD) = 65K WAV/dk (~3 dk). DAIMA `/root/`'a extract et: `tar --no-same-owner -xzf ... -C /root/issai/extracted/`. `set -e` + tar chown hatası = extraction ~8K'da ölür.
- **2. round Qwen training**: ISSAI pairs (`ml/whisper/datasets/issai/issai_pairs_clean.jsonl`) + mevcut dataset (`ml/qwen/data/`) → `ml/qwen/scripts/prepare_dataset.py` → RunPod Qwen training.
- **RunPod pod configs**: `runpod/pods/*.json` + `runpod/setup/*.sh`. Yeni pod: `cd runpod && python create_pod.py issai|stage2|qwen|ollama`.
- **RunPod Cloud Inference (doğrulanan, 2026-04-07)**: `config.yaml` → `whisper.backend: runpod` + `.env` → `RUNPOD_INFERENCE_URL`. RTX 4090 EU-RO-1 pod'u, faster-whisper large-v3 + Ollama qwen2.5:7b. SSH tunnel + multipart upload ile **~850ms** toplam (local MLX ~6sn'den 7x hızlı). Detay: `runpod/README.md` "Cloud Inference" bölümü.
- **RunPod Cloud Inference kurulum**: Pod aç → `zstd` + Ollama + faster-whisper + `python-multipart` kur → CUDA symlink (`ln -sf /usr/local/lib/ollama/cuda_v12/libcublas.so.12 /usr/lib/x86_64-linux-gnu/`) → handler + server yükle → SSH tunnel (`ssh -f -N -L 18765:localhost:8765 -p <SSH_PORT> root@<IP>`). Pod restart sonrası Ollama + server tekrar başlatılmalı.
- **RunPod proxy vs SSH tunnel**: Proxy ~200ms overhead, SSH tunnel ~50ms. Tunnel: `ssh -f -N -L 18765:localhost:8765 -p <PORT> root@<IP>`. `.env` → `RUNPOD_INFERENCE_URL=http://localhost:18765/inference`.
- **config.py .env yüklüyor**: `backend/src/voiceflow/core/config.py` repo root'taki `.env` dosyasını startup'ta `os.environ.setdefault()` ile yüklüyor. AppDelegate'in env geçirmesine gerek yok.
