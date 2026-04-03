# VoiceFlow — Sistem Mimarisi

## Mevcut Durum (v0.5, Çalışıyor)

```
[Mac — Apple Silicon]
├── Swift Menu Bar App (MVVM)
│   ├── AppViewModel      (@Observable — tüm state + iş mantığı)
│   ├── MenuBarController (NSMenu UI — AppViewModel'i observe eder)
│   ├── BackendService    (actor, BackendServiceProtocol impl)
│   ├── HotkeyManager     (Fn double-tap → kayıt başlat/durdur)
│   └── PasteService      (Clipboard + CGEvent Cmd+V)
│
└── Python Backend (FastAPI, port 8765)
    ├── api/routes.py        (HTTP katmanı — sadece request/response)
    ├── services/recording.py (RecordingService — iş mantığı)
    ├── core/interfaces.py   (AbstractTranscriber, AbstractCorrector)
    ├── audio/capture.py     (sounddevice, 16kHz mono float32)
    ├── transcription/       (mlx-whisper — Apple Silicon MLX)
    ├── correction/          (mlx-lm Qwen 7B — isteğe bağlı)
    └── db/storage.py        (aiosqlite — voiceflow.db, DB_PATH via config.yaml)
```

**Çalışan özellikler (v0.5):**
- Tamamen local, internet bağlantısı yok
- Apple Silicon MLX ile GPU hızlandırması
- Fn double-tap hotkey (push-to-talk + toggle)
- Auto-paste (Accessibility izni gerekli)
- Türkçe + İngilizce + otomatik dil algılama
- LLM düzeltme isteğe bağlı (~4GB, açıkken)
- SQLite persistent history (`voiceflow.db` repo root, `DB_PATH` ile configure edilir)
- Mod sistemi: General / Engineering / Office
- Kullanıcı profili: UUID, ad, departman
- Onboarding sihirbazı (ilk açılış)
- Server mode: Settings → Server URL + API Key → uzak GPU backend
- JWT auth + tenant izolasyonu (server mode)
- Admin web UI (Jinja2 Bootstrap 5) + usage dashboard
- Audit log + KVKK veri silme API
- Kişisel Sözlük (user_dictionary) + Sesli Şablonlar (snippets)
- Knowledge Base (ChromaDB RAG, MiniLM embeddings)
- Style/ton per-context (bundle ID → formal/casual/technical)
- LLM backend seçimi: Local MLX / Cloud RunPod Ollama / Alibaba DashScope qwen-max
- Fine-tuned LoRA adapter (Qwen2.5-7B, 39MB, `ml/qwen/adapters_mlx/`) — 1. round tamamlandı, `config.yaml` `llm.adapter_path` ile aktif
- Yanıt süresi: ~0.5s (LLM kapalı), ~3.5s (local 7B), ~1.5s (Alibaba cloud)

---

## Web — Marketing Landing Page (`web/`)

**Stack:** Next.js 14.2.5 · Tailwind CSS · Framer Motion · TypeScript

```
web/src/
├── app/
│   ├── page.tsx          ← tüm section'ları sıralar
│   ├── layout.tsx        ← global metadata, font, layout
│   └── globals.css       ← design tokens, animasyon keyframe'leri
├── components/
│   ├── sections/         ← Hero, Stats, Speed, HowItWorks, Features, Security, Testimonials, CTA
│   ├── layout/           ← Navbar (scroll-aware), Footer
│   └── ui/               ← Button, Card, Badge, GradientText, FadeUp, Container
├── lib/constants.ts      ← tüm copy ve veri (type-safe sabitler)
└── types/index.ts        ← NavLink, Feature, Stat, Testimonial, PricingTier vb.
```

**Çalıştır:** `cd web && npm run dev` → http://localhost:3000

**İçerik değişikliği:** Sadece `src/lib/constants.ts` düzenle.

**Eksik / TODO:**
- Pricing section (`PricingTier` tipi hazır ama henüz section yok)
- Social linkler placeholder (`twitter.com` / `linkedin.com` — gerçek URL'ler girilmeli)
- Trusted logos text — gerçek SVG logolar eklenecek
- Footer link'leri çoğu `#` — canlıya geçmeden önce doldurulacak

---

## Mimari Prensipler

### Backend — Layered Architecture
```
HTTP Layer  (api/routes.py)       ← request validate → service → response
Service     (services/recording.py) ← iş mantığı, orchestration
Interface   (core/interfaces.py)  ← AbstractTranscriber, AbstractCorrector
Impl        (transcription/, correction/) ← MLX veya NVIDIA impl
Data        (db/storage.py)       ← SQLite CRUD
```
- Routes'ta sıfır iş mantığı — sadece HTTP
- `RecordingService(transcriber, corrector)` constructor injection → testable
- `app.state.recording_service` via `Depends(get_service)` → FastAPI DI

### Swift — MVVM + Protocol DI
```
View        (MenuBarController, HistoryView, SettingsView)
ViewModel   (AppViewModel @Observable)
Service     (BackendService actor, BackendServiceProtocol)
Model       (Models.swift — LanguageMode, AppMode, TranscriptionResult)
```
- `AppViewModel` tüm state + iş mantığı; view'lar sadece gösterir
- `BackendServiceProtocol` → test/preview için mock inject edilebilir
- `@Observable` — sadece değişen property view'ı yeniden çizer

---

## Deployment Modları

### Mod A: Local (Mac)
```
[Mac]
├── Swift App
└── Python Backend (localhost:8765)
    ├── mlx-whisper (Apple Silicon GPU)
    └── mlx-lm Qwen 7B (isteğe bağlı, ~4GB)
```

### Mod B: Local + Cloud LLM
```
[Mac]
├── Swift App
└── Python Backend (localhost:8765)
    ├── mlx-whisper (Apple Silicon GPU — local)
    └── OllamaCorrector → RunPod Ollama veya Alibaba DashScope
```
- `config.yaml` `llm.backend: ollama` + `llm.endpoint` ile seçilir (AppDelegate runtime'da override eder)
- `BACKEND_MODE=local` kalır — faster-whisper/JWT gerekmez
- Settings'ten 3 seçenek: Local MLX / Cloud RunPod / Alibaba qwen-max

### Mod C: Server (Kurumsal, On-Premise)
```
[Mac — Thin Client]                    [Şirket / RunPod Sunucusu]
├── Swift App                   →      ├── FastAPI + RecordingService
│   ├── Ses kaydı (local)  HTTPS+VPN   ├── faster-whisper large-v3 (CUDA)
│   ├── Server URL config               ├── Ollama + Qwen 7B (GPU)
│   └── JWT auth                       ├── SQLite (history + config)
│                                      └── JWT middleware + tenant izolasyon
```
- Mac sadece ses kaydeder, işleme sunucuda
- Veri şirket ağından dışarı çıkmaz
- `config.yaml` `backend.mode: server` ile seçilir

---

## Hız (Ölçülmüş)

| Ortam | Whisper | LLM | Toplam |
|---|---|---|---|
| Mac M1/M2 (LLM kapalı) | ~0.3–0.5s | — | ~0.5s |
| Mac M1/M2 (MLX Qwen 7B) | ~0.3–0.5s | ~3–4s | ~3.5–4.5s |
| Mac + Alibaba qwen-max | ~0.3–0.5s | ~0.7–1s | ~1.5s |
| Mac + RunPod Ollama | ~0.3–0.5s | ~0.5–1s | ~1–1.5s |
| RTX 4090 server | ~0.2–0.3s | ~0.5–1s | ~0.8–1.3s |
| Mac + fine-tuned adapter (1. round) | ~0.3–0.5s | ~0.5–1s | ~1s |

---

## Veri Akışı

```
1. Fn double-tap → AppViewModel.startRecording()
2. BackendService.startRecording() → POST /api/start
3. Ses kaydı (Mac'te local, sounddevice)
4. Fn double-tap → AppViewModel.stopAndTranscribe()
5. BackendService.stopRecording() → POST /api/stop
   Headers: X-User-ID, X-Active-App, [X-Window-Title, X-Selected-Text — K4]
6. RecordingService.stop():
   a. AudioCapture.stop() → numpy array
   b. MLX executor → WhisperTranscriber.transcribe() (~0.3s)
   c. Dictionary substitution (user_dictionary)
   d. Snippet match (snippets tablosu)
   e. (enabled) → LLMCorrector.correct() [LLM_ADAPTER_PATH set ise fine-tuned LoRA adapter ile]
                    veya OllamaCorrector.correct_async()
      + RAG context injection (ChromaDB, KB varsa)
      + App tone override (bundle ID → formal/casual/technical)
      + [K4] Window title + selected text context injection
   f. db.save_transcription() → SQLite
7. TranscriptionResponse → Mac
8. AppViewModel → PasteService.pasteText() → Cmd+V
9. [K4] Training Mode açıksa → Training Pill göster
```

---

## Güvenlik

1. **VPN** — Şirket ağı erişim şartı (IT yönetir)
2. **API Key** — `X-Api-Key` header, server modunda zorunlu
3. **HTTPS** — TLS (production deployment'ta)
4. **On-Premise** — Ses + transkript şirket sunucusundan çıkmaz
5. **Audit** — Her transkripsiyon SQLite'a user_id ile kaydedilir

---

## Bilinen Kısıtlar

- Fn key release eventi macOS'ta güvenilmez → double-tap birincil yöntem
- Her Swift binary değişikliği Accessibility iznini sıfırlar
- MLX thread-safe değil → `ThreadPoolExecutor(max_workers=1)` (server modda sorun yok)
- Küçük LLM'ler (1.5B, 3B) Türkçe'de hallüsinasyon → minimum 7B
- Mac App Store sandbox global hotkey + paste'i engeller → DMG dağıtım şart
