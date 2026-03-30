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
│   └── auth.py                # X-Api-Key middleware
├── core/
│   └── interfaces.py          # AbstractTranscriber, AbstractCorrector, AbstractRetriever (ABCs)
├── services/
│   ├── recording.py           # RecordingService — TÜM iş mantığı
│   ├── dictionary.py          # apply_dictionary() — word-boundary substitution
│   └── snippets.py            # apply_snippets() — exact-match expansion
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
    ├── chroma_retriever.py    # ChromaDB retrieval (RAG, Phase 2)
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
    def __init__(self, transcriber, corrector, retriever=None)
    def start() → None
    async def stop(user_id) → dict      # transcribe → dict → snippets → RAG → LLM → save
    def force_stop() → bool
    async def preload_models() → None
```
Pipeline sırası: **Whisper → Dictionary → Snippets → RAG retrieval → LLM correction → SQLite**

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
        corrector=_build_corrector(),
    )
    app.state.recording_service = service
    asyncio.create_task(service.preload_models())
    yield
```

---

## API Endpoint'leri

```
GET  /health                  → {status, model_loaded, llm_loaded}
GET  /api/status              → {status: str, is_recording: bool}
POST /api/start               → Kayıt başlat (400 if already recording)
POST /api/stop                → Durdur + transcribe [X-User-ID opsiyonel]
POST /api/force-stop          → Her zaman başarılı
POST /api/config              → {language?, task?, correction_enabled?, mode?, model?}
GET  /api/devices             → Ses girişi cihazları listesi
GET  /api/history             → SQLite geçmişi [?limit=&offset=&user_id=]
DELETE /api/history           → Tüm geçmişi sil
POST /api/context/ingest      → Klasör indexle (async, ChromaDB)
GET  /api/context/status      → {count, is_ready, is_empty}
DELETE /api/context           → Knowledge base'i temizle
GET  /api/dictionary          → Kullanıcı sözlüğü [X-User-ID]
POST /api/dictionary          → {trigger, replacement, scope}
DELETE /api/dictionary/{id}   → Kişisel entry sil
GET  /api/snippets            → Snippet listesi [X-User-ID]
POST /api/snippets            → {trigger_phrase, expansion, scope}
DELETE /api/snippets/{id}     → Kişisel snippet sil
```

**Auth:** `X-Api-Key` header — `BACKEND_MODE=server` iken zorunlu, local'de no-op.

---

## TranscriptionResponse

```python
{
    "text": "Bugün hava çok güzel.",
    "raw_text": "bugun hava cok guzel",  # sadece düzeltildiyse dolu
    "corrected": true,
    "language": "tr",
    "duration": 3.45,
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

### Local (Mac, `BACKEND_MODE=local`)
```
HOST=127.0.0.1
transcriber = WhisperTranscriber (mlx-whisper)
corrector   = LLMCorrector (mlx-lm, Qwen 7B 4-bit)
auth        = no-op
```

### Server (NVIDIA, `BACKEND_MODE=server`)
```
HOST=0.0.0.0
transcriber = FasterWhisperTranscriber (NVIDIA CUDA)
corrector   = OllamaCorrector (httpx → Ollama OpenAI-compat API)
auth        = X-Api-Key validation (API_KEYS env var)
```
Env değişkenleri:
```bash
BACKEND_MODE=server
WHISPER_MODEL=large-v3         # faster-whisper model
LLM_MODEL=qwen2.5:7b           # Ollama model adı
LLM_ENDPOINT=http://ollama:11434
API_KEYS=key1,key2,key3
```

---

## Kritik Implementation Detayları

- **MLX thread safety:** `ThreadPoolExecutor(max_workers=1, thread_name_prefix="mlx")` — Metal GPU tek thread
- **Lazy loading:** Model ilk kullanımda yükler, `_ensure_model_loaded()` idempotent
- **LLM on-demand:** Correction açılınca yükle, kapanınca unload (~4GB boşalt)
- **Metal cache:** Her inference sonrası `mx.metal.clear_cache()` — bellek sızıntısı önler
- **Ollama async:** `correct_async()` → `httpx.AsyncClient` — MLX executor'ı bloklamaz
- **Mode capture:** `active_mode = corrector.config.mode` → concurrent `/api/config` race'i önler
- **faster-whisper:** numpy array değil BytesIO alır → `soundfile.write(buf, audio, sr, format="WAV")`
- **SQLite migration:** `PRAGMA table_info` + `ALTER TABLE ADD COLUMN` — ORM migration yok
- **Log:** `/tmp/voiceflow.log`, `/api/stop`'ta timing logları (Whisper ms, LLM ms, total ms)

---

## SQLite Schema (`~/.voiceflow/voiceflow.db`)

```sql
CREATE TABLE transcriptions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT    NOT NULL DEFAULT (datetime('now')),
    text       TEXT    NOT NULL,
    raw_text   TEXT,
    corrected  INTEGER DEFAULT 0,
    language   TEXT,
    duration   REAL,
    mode       TEXT    DEFAULT 'general',
    user_id    TEXT
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
    scope       TEXT NOT NULL DEFAULT 'personal'  -- 'personal' | 'team'
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
| `general` | ASCII Türkçe → düzgün Türkçe (ç,ş,ğ,ı,ö,ü) |
| `engineering` | Teknik terimler, API/değişken isimleri değişmez |
| `office` | Resmi dil, kısaltma açma, iş yazışması tonu |

Tüm modlar aynı few-shot örnekleri kullanır (3 örnek). Sadece system prompt değişir.

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

## Phase 2 — Context Engine (Aktif, v0.4)

```
backend/src/voiceflow/context/
├── chroma_retriever.py   # ChromaRetriever: MiniLM embeddings + ChromaDB
└── ingestion.py          # ingest_folder() → parse → embed → store
```

- **Embeddings:** `all-MiniLM-L6-v2` (CPU, ~22MB, lazy loaded)
- **Store:** ChromaDB `~/.voiceflow/chroma/`, `tenant="default"`
- **Retrieval:** top-3 chunks inject edilir LLM correction prompt'una
- **Lazy:** RecordingService'e opsiyonel 3. parametre — `retriever=None` ise RAG atlanır
