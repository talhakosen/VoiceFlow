# VoiceFlow — Backend Mimarisi

## Stack

**Python 3.14, FastAPI, uvicorn, port 8765**
**Pattern:** Layered Architecture (HTTP → Service → Interface → Impl → Data)

---

## Modül Yapısı

```
backend/src/voiceflow/
├── main.py                    # FastAPI app, lifespan (DI), health endpoint
├── api/
│   ├── routes.py              # HTTP katmanı: validate → service → response
│   ├── auth.py                # Middleware: X-Api-Key (local) / JWT Bearer (server)
│   ├── auth_routes.py         # /auth/register, /auth/login, /auth/refresh, /auth/me
│   └── admin_routes.py        # /admin/users CRUD (admin+ only, tenant isolated)
├── core/
│   └── interfaces.py          # AbstractTranscriber, AbstractCorrector, AbstractRetriever (ABCs)
├── services/
│   ├── recording.py           # RecordingService — TÜM iş mantığı
│   ├── auth_service.py        # JWT create/decode, bcrypt, require_role() dependency
│   ├── dictionary.py          # apply_dictionary() — 2-pass word-boundary substitution
│   ├── snippets.py            # apply_snippets() — exact-match expansion
│   ├── smart_dictionary.py    # build_smart_dictionary() — kod tabanından identifier çıkar, Türkçe fonetik varyantları user_dictionary'e ekler (scope='smart')
│   └── symbol_indexer.py      # build_symbol_index() — class/func/struct sembollerini file_path+line_number ile SQLite'a yazar; lookup_symbol() fuzzy arama
├── db/
│   └── storage.py             # aiosqlite CRUD (~/.voiceflow/voiceflow.db)
├── audio/
│   └── capture.py             # sounddevice ses kaydı, force_reset()
├── transcription/
│   ├── whisper.py             # MLX Whisper (local mode)
│   └── faster_whisper.py      # NVIDIA faster-whisper (server mode)
├── correction/
│   ├── llm_corrector.py       # mlx-lm Qwen 7B (local mode)
│   └── ollama_corrector.py    # Ollama HTTP client (server mode)
└── context/
    ├── chroma_retriever.py    # ChromaDB retrieval (RAG)
    └── ingestion.py           # Klasör indexleme → ChromaDB
```

---

## Katman Sorumlulukları

### HTTP Katmanı (`api/routes.py`)
Sıfır iş mantığı. Sadece:
1. Request'i Pydantic ile validate et
2. `Depends(get_service)` ile RecordingService al
3. Service metodunu çağır
4. Response döndür

### RecordingService (`services/recording.py`)
Tüm pipeline koordinasyonu:
```python
class RecordingService:
    def __init__(self, transcriber, corrector)
    def start() → None
    async def stop(user_id, cmd_intervals=None, ...) → dict
    def force_stop() → bool
    async def preload_models() → None
```
Pipeline sırası: **Whisper (+Symbol Injection) → Dictionary → Snippets → LLM correction → SQLite**

**Cmd-interval injection** (`cmd_intervals` doluysa, `_transcribe_segmented()`):
Ses numpy array olarak cmd sınırlarında bölünür. Her segment ayrı Whisper → cmd-held segmentlere `inject_symbol_refs()` uygulanır → normal segmentler olduğu gibi bırakılır → birleştirilir.
Symbol injection sadece cmd-held segmentlerde çalışır (normal konuşmada injection yok). `word_timestamps` kullanılmaz.

**Smart Dictionary** (`services/smart_dictionary.py`): `POST /api/context/ingest` tetiklenince çalışır. Klasördeki `.swift/.dart/.py/.ts` dosyalarını tarar, PascalCase/camelCase identifier'ları regex ile çıkarır, `_TURKISH_VARIANTS` ile Türkçe fonetik varyantlar üretir (örn. `SupabaseSavedOutfitRepository` → `"superbase saved outfit reposteri"`) ve `user_dictionary` tablosuna `scope='smart'` ile ekler. Tekrar indexlemede var olan trigger'lar üzerine yazılmaz.

**2-pass Dictionary** (`services/dictionary.py`): İki geçişte uygular — ilk geçiş kısa trigger'ları dönüştürür (`super bass` → `Supabase`), ikinci geçiş ortaya çıkan yeni eşleşmeleri yakalar (`Supabase saved outfit repository` → `SupabaseSavedOutfitRepository`).

**Symbol Index** (`services/symbol_indexer.py`): `POST /api/context/ingest` sonrası çalışır. Swift/Dart/Python/TS/Go/Kotlin dosyalarından class/struct/enum/func sembollerini regex ile çıkarır, `symbol_index` tablosuna `file_path + line_number` ile yazar. `GET /api/symbol/lookup?q=HistoryRow` → `VoiceFlowApp/Sources/HistoryView.swift:82` döner.

`inject_symbol_refs(text, user_id)` — **sadece cmd-held segmentler için çağrılır** (normal konuşmada injection yok):
- **Pass 0: directory matching** — `symbol_index.file_path` + filesystem walk'tan dizin adları toplanır; her kelime (ve ardışık 2 kelime bigram) JW ile karşılaştırılır. `"voiceflow"` → `@VoiceFlowApp/`, `"Voice flow"` (Whisper split) → bigram `"voiceflow"` → `@VoiceFlowApp/`. Eşik: 0.82 JW veya prefix bonus (≥5 karakter prefix = 0.95 skor).
- Pass 1: exact PascalCase token → DB exact match
- Pass 2: JW fuzzy PascalCase (OutService → AuthService)
- Pass 3: phonetic sliding window ("recording service" → RecordingService)

Sözcük tetikleyici yok ("at/et/folder" kaldırıldı). Cmd tuşu = tek injection sinyali.

**Snippet matching notu:** `apply_snippets()` tüm metni trigger ile karşılaştırır (tam eşleşme). Whisper cümle sonuna noktalama ekler — bu nedenle karşılaştırma öncesi `rstrip(".,!?;:")` uygulanır. Snippet expand olduysa `snippet_used=True` response'a eklenir; Training Pill bu durumda gösterilmez.

Constructor injection → test için mock takılabilir.

### Interfaces (`core/interfaces.py`)
```python
class AbstractTranscriber(ABC):
    def transcribe(audio, sample_rate) → TranscriptionResult
    def _ensure_model_loaded() → None
    def unload() → None

class AbstractCorrector(ABC):
    config: CorrectorConfig   # .enabled, .mode
    def correct(text, language) → str
    def _ensure_model_loaded() → None
    def unload() → None
```
MLX veya NVIDIA implementasyonu bağımsız olarak takılabilir.

### Dependency Injection (`main.py`)
```python
@asynccontextmanager
async def lifespan(app):
    await init_db()
    service = RecordingService(
        transcriber=_build_transcriber(),  # BACKEND_MODE'a göre seçilir
        corrector=_build_corrector(),      # LLM_BACKEND veya LLM_ENDPOINT'e göre seçilir
    )
    app.state.recording_service = service
    asyncio.create_task(service.preload_models())
    yield
```

**Corrector seçim mantığı** (`_build_corrector()`):
- `LLM_BACKEND=ollama` → OllamaCorrector
- `LLM_ENDPOINT` set edilmişse → OllamaCorrector (URL doğrudan kullanılır)
- `BACKEND_MODE=server` → OllamaCorrector
- Hiçbiri yoksa → MLX LLMCorrector

**LLMCorrector LoRA adapter**: `LLM_ADAPTER_PATH` env var set ise fine-tuned adapter yüklenir (örn. `scripts/training/adapters_mlx`). Yoksa vanilla Qwen2.5-7B çalışır.

---

## API Endpoint'leri

```
# Auth (public — token gerektirmez)
POST /auth/register           → {email, password} → {user_id, email, tenant_id}
POST /auth/login              → {email, password} → {access_token, refresh_token, token_type}
POST /auth/refresh            → {refresh_token}   → {access_token, token_type}
GET  /auth/me                 → Bearer token      → {user_id, email, tenant_id, role}

# Admin (admin+ role gerektirir, tenant isolated)
GET  /admin/users             → tenant'taki tüm kullanıcılar
PUT  /admin/users/{id}/role   → {role: "admin"|"member"|"superadmin"}
DELETE /admin/users/{id}      → soft delete (is_active=0)

# API (JWT Bearer veya X-Api-Key)
GET  /health                  → {status, model_loaded, llm_loaded}
GET  /api/status              → {status: str, is_recording: bool}
POST /api/start               → Kayıt başlat
POST /api/stop                → Durdur + transcribe
POST /api/force-stop          → Her zaman başarılı
POST /api/config              → {language?, task?, correction_enabled?, mode?, model?}
GET  /api/devices             → Ses girişi cihazları listesi
GET  /api/history             → SQLite geçmişi [?limit=&offset=] — tenant filtered
DELETE /api/history           → Geçmişi sil
POST /api/context/ingest      → Smart Dictionary + Symbol Index taraması (async, ChromaDB yok)
GET  /api/context/status      → {count: smart_dict_entry_count, is_ready, is_empty}
GET  /api/context/projects    → [{name, path, symbol_count}] + smart_word_count + total_symbols
DELETE /api/context           → kullanıcının smart dict (scope=smart) entry'lerini sil
GET  /api/symbol/lookup?q=X   → [{symbol_name, symbol_type, file_path, line_number}] fuzzy arama
POST /api/feedback            → {raw_whisper, model_output, user_action, user_edit, ...}
GET  /api/context/status      → {count, is_ready, is_empty}
DELETE /api/context           → Knowledge base'i temizle
GET  /api/dictionary          → Kullanıcı sözlüğü
POST /api/dictionary          → {trigger, replacement, scope}
DELETE /api/dictionary/{id}   → Kişisel entry sil
GET  /api/snippets            → Snippet listesi
POST /api/snippets            → {trigger_phrase, expansion, scope}
DELETE /api/snippets/{id}     → Kişisel snippet sil
```

**Auth:**
- `local` mode: X-Api-Key middleware (no-op), tüm API açık
- `server` mode: `Authorization: Bearer <JWT>` zorunlu; 401 → geçersiz/expired, 403 → yetersiz rol
- JWT payload: `{sub: user_id, tenant_id, role, exp}`
- `request.state`: `user_id`, `tenant_id`, `role` — tüm route'larda kullanılabilir

---

## TranscriptionResponse

```python
{
    "text": "Bugün hava çok güzel.",
    "raw_text": "bugun hava cok guzel",  # sadece düzeltildiyse dolu
    "corrected": true,
    "snippet_used": false,               # snippet expand olduysa true — Training Pill bu durumda gösterilmez
    "language": "tr",
    "duration": 3.45,
    "processing_ms": 1240,               # ses durma → paste arası toplam süre (ms)
    "id": 42                             # SQLite row ID
}
```

## ConfigRequest

```python
{
    "language": "tr",           # None = auto-detect
    "task": "transcribe",       # "transcribe" | "translate"
    "correction_enabled": true,
    "mode": "engineering",      # "general" | "engineering" | "office"
    "model": null
}
```

---

## Deployment Modları

### Local + Cloud LLM (Mac Whisper + RunPod Ollama) — Aktif Kullanım
```
BACKEND_MODE=local
LLM_BACKEND=ollama  (veya LLM_ENDPOINT set edilmiş)
HOST=127.0.0.1
transcriber = WhisperTranscriber (mlx-whisper, Mac)
corrector   = OllamaCorrector → RunPod RTX 4090 Ollama
auth        = no-op
```
Swift app, Settings → Recording → LLM Backend seçimine göre `LLM_BACKEND` ve `LLM_ENDPOINT` env var'larını backend'e geçirir. `.env` dosyasındaki `LLM_ENDPOINT` okunur.

### Local (Tam Mac, `BACKEND_MODE=local`)
```
HOST=127.0.0.1
transcriber = WhisperTranscriber (mlx-whisper)
corrector   = LLMCorrector (mlx-lm, Qwen 7B 4-bit, ~4GB)
auth        = no-op (X-Api-Key optional)
```

### Server (NVIDIA, `BACKEND_MODE=server`)
```
HOST=0.0.0.0
transcriber = FasterWhisperTranscriber (NVIDIA CUDA)
corrector   = OllamaCorrector (httpx → Ollama OpenAI-compat API)
auth        = JWT Bearer zorunlu + X-Api-Key fallback
```
Env değişkenleri:
```bash
BACKEND_MODE=server
WHISPER_MODEL=large-v3
LLM_MODEL=qwen2.5:7b
LLM_ENDPOINT=http://ollama:11434
API_KEYS=key1,key2,key3
JWT_SECRET=<strong-random-secret>
JWT_ACCESS_TTL_MINUTES=60
```

---

## Kritik Implementation Detayları

- **MLX thread safety:** `ThreadPoolExecutor(max_workers=1, thread_name_prefix="mlx")` — Metal GPU tek thread
- **Lazy loading:** Model ilk kullanımda yükler, `_ensure_model_loaded()` idempotent
- **LLM on-demand:** Correction açılınca yükle, kapanınca unload (~4GB boşalt)
- **Metal cache:** Her inference sonrası `mx.metal.clear_cache()` — bellek sızıntısı önler
- **CJK hallucination guard:** LLM çıktısında Latin/Türkçe dışı karakter (örn. Japonca 取得, Çince 的) varsa `re.sub` ile silinir — Qwen'in CJK eğitim verisinden kaynaklanan sızma önlenir
- **Whisper hallucination — loop guard:** `_strip_hallucination_loop()` — unigram/bigram/trigram 3+ tekrar algılar, kuyruk silinir (ör. "Yar Yar Yar...")
- **Whisper hallucination — fixed phrase guard:** `_strip_hallucination_phrases()` — "İzlediğiniz için teşekkür ederim", "Altyazı M.K.", "Thank you for watching" gibi YouTube training data kalıntılarını metnin sonundan siler. Liste `_HALLUCINATION_PHRASES` sabitinde, DB tablosuna geçiş Quality Monitor ile planlandı (bkz. `docs/discussions/006-quality-monitor.md`)
- **Ollama async:** `correct_async()` → `httpx.AsyncClient` — MLX executor'ı bloklamaz
- **Mode capture:** `active_mode = corrector.config.mode` → concurrent `/api/config` race'i önler
- **faster-whisper:** numpy array değil BytesIO alır → `soundfile.write(buf, audio, sr, format="WAV")`
- **SQLite migration:** `PRAGMA table_info` + `ALTER TABLE ADD COLUMN` — ORM migration yok
- **Log:** `/tmp/voiceflow.log`, `/api/stop`'ta timing logları (Whisper ms, LLM ms, total ms)

---

## SQLite Schema (`~/.voiceflow/voiceflow.db`)

```sql
CREATE TABLE users (
    id            TEXT PRIMARY KEY,         -- UUID
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,            -- bcrypt
    tenant_id     TEXT NOT NULL DEFAULT 'default',
    role          TEXT NOT NULL DEFAULT 'member',  -- member | admin | superadmin
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE transcriptions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    text          TEXT    NOT NULL,
    raw_text      TEXT,
    corrected     INTEGER DEFAULT 0,
    language      TEXT,
    duration      REAL,                    -- ses kaydı süresi (saniye)
    mode          TEXT    DEFAULT 'general',
    user_id       TEXT,
    tenant_id     TEXT    NOT NULL DEFAULT 'default',
    processing_ms INTEGER                  -- Whisper+LLM toplam süresi (ms)
);

CREATE TABLE config (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE user_dictionary (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    user_id     TEXT NOT NULL DEFAULT '',
    trigger     TEXT NOT NULL,
    replacement TEXT NOT NULL,
    scope       TEXT NOT NULL DEFAULT 'personal'  -- 'personal' | 'team' | 'smart'
);
-- scope='smart': build_smart_dictionary() tarafından otomatik eklenir, UI'da gösterilmez
-- scope='personal'/'team': kullanıcı tarafından manuel eklenir, Sözlük UI'da görünür

CREATE TABLE symbol_index (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      TEXT NOT NULL DEFAULT '',
    project_path TEXT NOT NULL DEFAULT '',
    file_path    TEXT NOT NULL,
    symbol_type  TEXT NOT NULL,   -- 'class' | 'struct' | 'func' | 'enum' | 'protocol' | ...
    symbol_name  TEXT NOT NULL,
    line_number  INTEGER NOT NULL
);

CREATE TABLE snippets (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id      TEXT NOT NULL DEFAULT 'default',
    user_id        TEXT NOT NULL DEFAULT '',
    trigger_phrase TEXT NOT NULL,
    expansion      TEXT NOT NULL,
    scope          TEXT NOT NULL DEFAULT 'personal'  -- 'personal' | 'team'
);
```

---

## Mod Sistemi — LLM Promptları

| Mode | System Prompt Odağı |
|---|---|
| `general` | ASCII Türkçe → düzgün Türkçe (ç,ş,ğ,ı,ö,ü), dolgu kelime temizleme |
| `engineering` | Teknik terimler, API/değişken isimleri değişmez |
| `office` | Resmi dil, kısaltma açma, iş yazışması tonu |

**Dolgu kelime temizleme** (tüm modlarda aktif): "gibi", "şey", "yani", "işte", "falan", "filan", "sanki", "hani" — anlamsız dolgu olarak kullanıldığında silinir, anlamlı kullanımlarda korunur.

Tüm modlar aynı few-shot örnekleri kullanır (7 örnek). Sadece system prompt suffix değişir.

---

## Bağımlılıklar (pyproject.toml)

```toml
# Tümü
mlx-whisper>=0.4.0
mlx-lm>=0.21.0
sounddevice>=0.5.0
fastapi>=0.109.0
uvicorn>=0.27.0
numpy>=1.24.0
httpx>=0.27.0
aiosqlite>=0.20.0

# Server modu (pip install voiceflow[server])
faster-whisper>=1.1.0
soundfile>=0.12.0
```

---

## Phase 2 — Smart Dictionary + Symbol Index (Aktif)

ChromaDB kaldırıldı. Embedding/RAG yok. İki hafif SQLite tabanlı sistem:

**Smart Dictionary** (`user_dictionary` tablosu, `scope='smart'`):
- Klasör taranır → PascalCase/camelCase identifier'lar → Türkçe fonetik varyantlar
- Whisper pipeline'da apply_dictionary() 2-pass ile uygular
- `GET /api/dictionary` sadece manual (personal/team) entry döner — 6K+ smart entry UI'ı ezmez
- `RecordingService.stop()` → `get_dictionary(include_smart=True)` ile hem manual hem smart entry'leri kullanır

**Symbol Index** (`symbol_index` tablosu):
- Klasör taranır → class/struct/func/enum → file_path + line_number
- Swift, Dart, Python, TypeScript, Kotlin, Go desteklenir
- `GET /api/symbol/lookup?q=HistoryRow` → `VoiceFlowApp/Sources/HistoryView.swift:82`
- Tam eşleşme → prefix → substring sırasıyla fuzzy match

---

## LLM Backend Seçimi (v0.5)

**3 seçenek** — Swift app Settings'ten `llmMode` UserDefaults key'i ile seçilir, AppDelegate env var'larını backend'e geçirir:

| llmMode | Env Vars | Corrector |
|---------|----------|-----------|
| `local` | `LLM_BACKEND=mlx` | LLMCorrector (mlx-lm Qwen 7B) |
| `cloud` | `LLM_BACKEND=ollama`, `LLM_ENDPOINT` (RunPod), `LLM_MODEL=qwen2.5:7b` | OllamaCorrector |
| `alibaba` | `LLM_BACKEND=ollama`, `LLM_ENDPOINT=https://dashscope-intl.aliyuncs.com/compatible-mode`, `LLM_MODEL=qwen-max`, `LLM_API_KEY` | OllamaCorrector |

**OllamaCorrector** OpenAI-compatible endpoint kullanan her servisle çalışır (Ollama, vLLM, mlx-lm server, DashScope).

---

## Katman 4 — Tamamlanan Backend Değişiklikleri

### ✅ Yeni Endpoint
```
POST /api/feedback   → {raw_whisper, model_output, user_action, user_edit, app_context}
```

### ✅ Yeni SQLite Tablosu
```sql
CREATE TABLE correction_feedback (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id    TEXT NOT NULL,
    user_id      TEXT,
    raw_whisper  TEXT NOT NULL,
    model_output TEXT NOT NULL,
    user_action  TEXT NOT NULL,   -- 'approved' | 'edited' | 'dismissed'
    user_edit    TEXT,
    app_context  TEXT,
    window_title TEXT,
    mode         TEXT,
    language     TEXT,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### ✅ Yeni Headers
`POST /api/stop`'a ek header'lar — Swift Context Capture'dan gelir:
```
X-Window-Title: "Re: Q3 Roadmap - Mail"   (max 300 char, sanitized)
X-Selected-Text: "Lütfen bütçeyi..."      (max 300 char, sanitized)
X-Cmd-Intervals: "2.16-10.19,22.82-25.78" (Cmd basılı saniye aralıkları)
```
Backend, `X-Window-Title` / `X-Selected-Text`'i OllamaCorrector'a "untrusted metadata" olarak iletir.
`X-Cmd-Intervals` varsa ses bölünür, o segmentlere symbol injection uygulanır.

### Fine-Tuning Scripts

```
backend/scripts/
├── data_gen/
│   ├── corruption_pipeline.py   ← clean text → simüle Whisper hataları (3K pair)
│   ├── process_issai.py         ← ISSAI 186K ses → faster-whisper large-v3 → ASR hata pair
│   │                               SHARD_INDEX/SHARD_TOTAL env → 3 paralel process destekler
│   ├── word_order_generator.py  ← Türkçe kelime sırası düzeltme pair (531 pair)
│   ├── word_order_pairs.jsonl   ← üretilen kelime sırası verisi
│   └── gecturk_pairs.jsonl      ← GECTurk-generation HF dataset (138K pair)
└── training/
    ├── prepare_dataset.py       ← tüm kaynaklar → train/valid/test.jsonl
    ├── train_runpod.py          ← Unsloth SFTTrainer, RTX 4090, batch=8, bf16
    ├── convert_adapter.py       ← HF PEFT adapter → MLX format (transpose lora_A/lora_B)
    ├── lora_config.yaml         ← MLX LoRA config (Qwen2.5-7B, rank=8)
    ├── adapters_mlx/            ← aktif MLX adapter (39MB) — LLM_ADAPTER_PATH bu dizini gösterir
    │   ├── adapters.safetensors
    │   ├── adapter_config.json
    │   └── raw/                 ← orijinal HF PEFT dosyaları (RunPod'dan indirildi)
    └── adapters_runpod/         ← eski referans (adapters_mlx/raw/ ile aynı içerik)
```

**Dataset kaynakları** (`prepare_dataset.py --sources`):
- `corruption_pairs.jsonl` — 3K sentetik Whisper hata simülasyonu
- `word_order_pairs.jsonl` — 531 Türkçe kelime sırası (SOV) düzeltme pair
- `gecturk_pairs.jsonl` — 138K GECTurk Türkçe gramer hata düzeltme (`mcemilg/GECTurk-generation`)
- `issai_pairs_all.jsonl` — 186K gerçek Whisper hata pair (ISSAI ses → large-v3 transkript) **(1. round'da yok, 2. round'a eklenecek)**
- 1. round toplam: ~141K pair (gecturk 138K + corruption 3K + word_order 531)
- 2. round hedef: ~327K pair (ISSAI 186K eklendikten sonra)

**Training durumu:**
- ✅ 1. round: 14115 adım, RTX 4090, ~5 saat, $3 — adapter `adapters_mlx/` altında
- 🔜 2. round: ISSAI bittikten sonra — gerçek Whisper hata çiftleri kaliteyi önemli artırır
