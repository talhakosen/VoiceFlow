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
│   └── storage.py             # aiosqlite CRUD (voiceflow.db — DB_PATH via config.yaml)
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

**Engineering mode symbol detection:** `stop()` içinde, dictionary/snippets adımından sonra, `active_mode == "engineering"` ise `inject_symbol_refs()` otomatik çağrılır. Tespit edilen semboller `symbol_refs` listesine eklenir, pasted text temiz kalır. Cmd basılı segment varsa ek olarak `_transcribe_segmented()` de çalışır.

**Cmd-interval injection** (`cmd_intervals` doluysa, `_transcribe_segmented()`):
Ses numpy array olarak cmd sınırlarında bölünür. Her segment ayrı Whisper → cmd-held segmentlere `inject_symbol_refs()` uygulanır. `word_timestamps` kullanılmaz.

**Smart Dictionary** (`services/smart_dictionary.py`): `POST /api/context/ingest` tetiklenince çalışır. Klasördeki `.swift/.dart/.py/.ts` dosyalarını tarar, PascalCase/camelCase identifier'ları regex ile çıkarır, `_TURKISH_VARIANTS` ile Türkçe fonetik varyantlar üretir (örn. `SupabaseSavedOutfitRepository` → `"superbase saved outfit reposteri"`) ve `user_dictionary` tablosuna `scope='smart'` ile ekler. Tekrar indexlemede var olan trigger'lar üzerine yazılmaz.

**Aho-Corasick Dictionary** (`services/dictionary.py`): `pyahocorasick` ile tek geçişte O(|metin|) eşleşme. 70K+ bundle entry için naif regex döngüsüne kıyasla ~275.000× daha hızlı (0.012ms/kayıt). Automaton `RecordingService` içinde cache'lenir — sadece `len(entries)` değiştiğinde (bundle yükle/sil, yeni entry) rebuild edilir (36ms). 2 pass yapılır: ilk geçiş kısa trigger'ları dönüştürür, ikinci geçiş zincirleme eşleşmeleri yakalar. Bkz. `docs/architecture/it-dictionary-bundle.md`.

**Symbol Index** (`services/symbol_indexer.py`): `POST /api/context/ingest` sonrası çalışır. **tree-sitter AST parser** ile Swift/Python/TS/Go/Kotlin dosyalarını parse eder — regex değil. `symbol_index_v2` tablosuna zengin metadata yazar (`parent_class`, `conformances`, `signature`, `return_type`, `visibility`). Backward-compat için `symbol_index` tablosuna da düz kayıt yapar. `.claude/worktrees/` ve `node_modules/` gibi gürültülü dizinler otomatik atlanır.

`generate_project_notes(path, user_id)` — ingest sonrası `{project_root}/.claude/project-notes.md` üretir: mimari pattern tespiti (MVVM, Service Layer, DI), kütüphane listesi, key symbols tablosu. Claude agent her konuşmada bu dosyayı otomatik okur.

`inject_symbol_refs(text, user_id)` — **engineering modda otomatik çağrılır** (Cmd şartsız):
- **Pass 0: directory matching** — dizin adları → `@VoiceFlowApp/` gibi ref
- Pass 1: exact PascalCase token → DB exact match
- Pass 2: JW fuzzy PascalCase (OutService → AuthService)
- Pass 3: phonetic sliding window ("recording service" → RecordingService)

Tespit edilen semboller `symbol_refs: ["BackendService → VoiceFlowApp/Sources/BackendService.swift:212"]` olarak response'a eklenir. Pasted text değişmez — semboller status bar'da 3s gösterilir.

**Snippet matching notu:** `apply_snippets()` tüm metni trigger ile karşılaştırır (tam eşleşme). Whisper cümle sonuna noktalama ekler — bu nedenle karşılaştırma öncesi `rstrip(".,!?;:")` uygulanır. Snippet expand olduysa `snippet_used=True` response'a eklenir; Training Pill bu durumda gösterilmez.

**AudioCapture `stop()` sıralaması** (`audio/capture.py`):
`stream.stop()` + `stream.close()` — state `STOPPED`'a çevrilmeden **önce** çağrılır. Nedeni: PortAudio callback'i `RecordingState.RECORDING` kontrolü yapar; state erken değiştirilirse son ses chunk'ları kaybolur. Doğru sıra: stream durdur → buffer drain → state güncelle.

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

**LLMCorrector LoRA adapter**: `config.yaml` `llm.adapter_path` set ise fine-tuned adapter yüklenir (`ml/qwen/adapters_mlx`). Yoksa vanilla Qwen2.5-7B çalışır.

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
GET  /health                  → {status, model_loaded, llm_loaded, whisper_model}
GET  /api/status              → {status: str, is_recording: bool}
POST /api/start               → Kayıt başlat
POST /api/stop                → Durdur + transcribe
POST /api/force-stop          → Her zaman başarılı
POST /api/config              → {language?, task?, correction_enabled?, mode?, model?}
GET  /api/devices             → Ses girişi cihazları listesi
GET  /api/history             → SQLite geçmişi [?limit=&offset=] — tenant filtered
DELETE /api/history           → Geçmişi sil
POST /api/context/ingest      → Smart Dictionary + Symbol Index taraması (async, ChromaDB yok)
GET  /api/context/status      → {count, symbol_count, last_indexed_at, last_index_path, is_ready, is_empty}
GET  /api/context/projects    → [{name, path, symbol_count}] + smart_word_count + total_symbols
DELETE /api/context           → kullanıcının smart dict (scope=smart) entry'lerini sil
GET  /api/symbol/lookup?q=X   → [{symbol_name, symbol_type, file_path, line_number}] fuzzy arama
POST /api/feedback            → {raw_whisper, model_output, user_action, user_edit, ...}
GET  /api/context/status      → {count, is_ready, is_empty}
DELETE /api/context           → Knowledge base'i temizle
GET  /api/dictionary          → Kullanıcı sözlüğü (personal + team, bundle gizli)
POST /api/dictionary          → {trigger, replacement, scope}
DELETE /api/dictionary/{id}   → Kişisel entry sil
POST /api/dictionary/bundle   → {bundle_path} → bundle JSON'ı DB'ye yükle (scope='bundle', UI'da gizli)
DELETE /api/dictionary/bundle → Tüm bundle entry'lerini sil
GET  /api/snippets            → Snippet listesi
POST /api/snippets            → {trigger_phrase, expansion, scope}
DELETE /api/snippets/{id}     → Kişisel snippet sil
GET  /api/it-dataset/next           → Rastgele kaydedilmemiş cümle (Yeni tab / Shuffle)
GET  /api/it-dataset/random         → Yeni shuffle (next ile aynı)
POST /api/it-dataset/record         → {index: sentence_id, whisper_output, audio_b64?} → kayıt kaydet
DELETE /api/it-dataset/record       → {wav_path} → kaydı sil
GET  /api/it-dataset/recorded       → En az 1 kaydı olan cümleler (Pratik tab)

# User Correction Training (Training Mode pill'inden tetiklenir)
POST /api/training/save-correction  → {wav_path, whisper_text, corrected_text} → WAV sakla + JSONL'e ekle
DELETE /api/training/pending-wav    → {wav_path} → pending WAV sil (dismiss/approve)
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
    "id": 42,                            # SQLite row ID
    "pending_wav_path": "/abs/path.wav", # X-Training-Mode=1 ise dolu; null otherwise
    "symbol_refs": ["BackendService → VoiceFlowApp/Sources/BackendService.swift:212"]  # engineering mode, null otherwise
}
```

**Pending WAV akışı:**
- `X-Training-Mode: 1` → `recording.py` pending WAV kaydeder → `pending_wav_path` response'a eklenir
- Swift Training Pill gösterilir
- Kullanıcı **Düzelt + Kaydet** → `POST /training/save-correction` → WAV `user_corrections/` klasörüne taşınır, `corrections.jsonl`'e eklenir
- Kullanıcı **Onayla / Dismiss / Timeout** → `DELETE /training/pending-wav` → WAV silinir
- JSONL format: `{"audio": "/abs/path.wav", "whisper_out": "...", "corrected": "..."}`

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
Swift app, Settings → Recording → LLM Backend seçimine göre `LLM_BACKEND` ve `LLM_ENDPOINT` env var'larını runtime'da backend'e geçirir. Default değerler `config.yaml`'dan (`llm.backend`, `llm.endpoint`).

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
`config.yaml` (non-secret):
```yaml
backend:
  mode: server
whisper:
  server_model: large-v3
llm:
  model: qwen2.5:7b
  endpoint: http://ollama:11434
auth:
  jwt_access_ttl_minutes: 60
```
`.env` (secrets):
```bash
API_KEYS=key1,key2,key3
JWT_SECRET=<strong-random-secret>
```

---

## Kritik Implementation Detayları

- **AudioCapture.stop() race fix:** `stream.stop()` → state=STOPPED sırası kritik. Stream önce durdurulur (buffer flush callback'e gider, state hâlâ RECORDING), sonra state STOPPED olur. Ters sıra = son audio chunk'ları atılır.
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

## SQLite Schema (`voiceflow.db` — repo root, `config.yaml` `backend.db_path`)

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
-- scope='smart':    build_smart_dictionary() tarafından otomatik eklenir, UI'da gösterilmez
-- scope='bundle':   IT Bundle — fonetik Türkçe → doğru IT terimi (70K+ entry), UI'da gizli, pipeline'da aktif
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

-- Ses Eğitimi: cümle havuzu (whisper_sentences.jsonl'den import edilir, one-time migration)
CREATE TABLE training_sentences (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    training_set TEXT NOT NULL DEFAULT 'it_dataset',  -- 'it_dataset' | 'akbank_v1' | ...
    persona      TEXT,
    scenario     TEXT,
    text         TEXT NOT NULL
);

-- Ses Eğitimi: kullanıcı kayıtları
CREATE TABLE training_recordings (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    sentence_id  INTEGER NOT NULL REFERENCES training_sentences(id),
    training_set TEXT NOT NULL DEFAULT 'it_dataset',
    wav_path     TEXT NOT NULL,
    whisper_out  TEXT,        -- Whisper'ın duyduğu (ground truth karşılaştırması için)
    duration_ms  INTEGER,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

`training_set` parametresi ile birden fazla veri seti desteklenir (IT, Akbank, Turkcell vb.).
İlk `/api/it-dataset/next` çağrısında `whisper_sentences.jsonl` otomatik import edilir.

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
- Whisper pipeline'da Aho-Corasick ile uygulanır
- `GET /api/dictionary` sadece manual (personal/team) entry döner — 6K+ smart entry UI'ı ezmez
- `RecordingService.stop()` → `get_dictionary(include_smart=True)` ile personal + team + smart + bundle entry'lerini kullanır

**IT Bundle** (`user_dictionary` tablosu, `scope='bundle'`):
- 1.660 base terim × 42 Türkçe çekim eki = ~70.000 entry
- Türkçe fonetik → doğru IT terimi: "invayrınmınt" → "environment", "arketçır" → "architecture"
- `POST /api/dictionary/bundle {bundle_path}` ile yüklenir; mevcut bundle önce temizlenir
- Bkz. `ml/dictionary/generate_it_bundle.py` ve `docs/architecture/it-dictionary-bundle.md`

**Symbol Index** (`symbol_index` + `symbol_index_v2` tabloları):
- tree-sitter AST ile parse edilir (Swift/Python/TS/Go/Kotlin)
- `symbol_index_v2`: zengin metadata (parent_class, conformances, signature, return_type, visibility, is_static)
- `symbol_index`: backward-compat düz kayıt (inject_symbol_refs bu tabloyu sorgular)
- `.claude/project-notes.md` otomatik üretilir — Claude agent context'i
- Engineering mode'a geçişte (>5dk stale ise) arka planda otomatik re-index tetiklenir
- `app.state.last_index_paths[user_id]` — son ingest path in-memory saklanır

---

## LLM Backend Seçimi (v0.5)

**3 seçenek** — Swift app Settings'ten `llmMode` UserDefaults key'i ile seçilir, AppDelegate env var'larını backend'e geçirir:

| llmMode | Env Vars | Corrector |
|---------|----------|-----------|
| `local` | `LLM_BACKEND=mlx` | LLMCorrector (mlx-lm Qwen 7B) |
| `cloud` | `config.yaml llm.backend=ollama` + `llm.endpoint` (RunPod), `LLM_MODEL=qwen2.5:7b` | OllamaCorrector |
| `alibaba` | `llm.backend=ollama`, `llm.endpoint=dashscope-intl...`, `llm.model=qwen-max`, `LLM_API_KEY` (.env secret) | OllamaCorrector |

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
X-Training-Mode: "1"                       (Training Mode açıksa — pending WAV kaydedilir)
```
Backend, `X-Window-Title` / `X-Selected-Text`'i OllamaCorrector'a "untrusted metadata" olarak iletir.
`X-Cmd-Intervals` varsa ses bölünür, o segmentlere symbol injection uygulanır.
`X-Training-Mode=1` ise her kayıt sonrası WAV geçici olarak `ml/whisper/datasets/user_corrections/pending/` klasörüne kaydedilir; path `pending_wav_path` alanı ile response'a eklenir.

### ML Scripts (`ml/`)

```
ml/
├── qwen/                        ← Qwen ASR correction fine-tuning
│   ├── scripts/
│   │   ├── prepare_dataset.py   ← kaynaklar → datasets/train/valid/test.jsonl
│   │   ├── train_runpod.py      ← Unsloth SFTTrainer, RTX 4090, batch=8, bf16
│   │   ├── convert_adapter.py   ← HF PEFT → MLX format (transpose lora_A/lora_B)
│   │   ├── evaluate.py          ← WER/CER/exact-match raporu
│   │   └── lora_config.yaml     ← MLX LoRA config (Qwen2.5-7B, rank=8)
│   ├── datasets/
│   │   ├── train.jsonl          ← 244K pair (Qwen chat format)
│   │   ├── valid.jsonl          ← 30K pair
│   │   └── test.jsonl           ← 30K pair
│   ├── adapters_mlx/            ← aktif MLX adapter (39MB) — config.yaml llm.adapter_path
│   ├── data/                   ← ham training pair'leri (corruption, gecturk, oneri vb.)
│   └── generators/             ← pair üretecileri (claude, corruption, word_order vb.)
├── whisper/                     ← Whisper fine-tuning
│   ├── whisper_issai_finetune.py ← Katman 1: ISSAI 164K → voiceflow-whisper-tr
│   ├── whisper_poc_finetune.py  ← PoC script
│   ├── process_issai.py         ← ISSAI WAV → Whisper error pairs
│   ├── generators/              ← sentence_generator, persona_terms, tts_generator
│   └── datasets/
│       ├── issai/               ← issai_pairs_clean.jsonl (164K)
│       └── it_dataset/          ← whisper_sentences.jsonl (4495) + recordings/ (WAV)
└── runpod/                      ← Pod config + setup scripts
    ├── pods/                    ← issai_h100.json, qwen_4090.json, ollama_inference.json
    ├── setup/                   ← issai.sh, qwen.sh, ollama.sh
    └── create_pod.py            ← python create_pod.py issai|qwen|ollama
```

**Qwen dataset kaynakları** (`prepare_dataset.py --sources`):
- `ml/qwen/data/corruption_pairs.jsonl` — 3K sentetik Whisper hata simülasyonu
- `ml/qwen/data/word_order_pairs.jsonl` — 531 Türkçe kelime sırası (SOV) düzeltme pair
- `ml/qwen/data/gecturk_pairs.jsonl` — 138K GECTurk Türkçe gramer hata düzeltme
- `ml/whisper/datasets/issai/issai_pairs_all.jsonl` — 186K gerçek Whisper hata pair **(2. round'a eklenecek)**
- 1. round toplam: ~141K pair (gecturk 138K + corruption 3K + word_order 531)
- 2. round hedef: ~327K pair (ISSAI 186K eklendikten sonra)

**Training durumu:**
- ✅ 1. round: 14115 adım, RTX 4090, ~5 saat, $3 — adapter `adapters_mlx/` altında
- 🔜 2. round: ISSAI bittikten sonra — gerçek Whisper hata çiftleri kaliteyi önemli artırır
