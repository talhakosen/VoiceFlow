# VoiceFlow — Backend Mimarisi

## Mevcut Backend (v0.1, Çalışıyor)

**Stack:** Python 3.14, FastAPI, uvicorn, port 8765

### Modül Yapısı
```
backend/src/voiceflow/
├── main.py           # FastAPI app, lifespan, health endpoint
├── cli.py            # Terminal tabanlı alternatif (ENTER ile kayıt)
└── api/
│   └── routes.py     # Tüm HTTP endpoint'leri
├── audio/
│   └── capture.py    # sounddevice ile ses kaydı
├── transcription/
│   └── whisper.py    # mlx-whisper wrapper
└── correction/
    └── llm_corrector.py  # mlx-lm Qwen 7B wrapper
```

### API Endpoint'leri (Doğrulanmış)
```
GET  /health          → {status, model_loaded, model_loading, llm_loaded}
GET  /api/status      → {status: str, is_recording: bool}
POST /api/start       → Kayıt başlat (zaten kayıttaysa 400)
POST /api/stop        → Durdur + transkripsiyon yap
POST /api/force-stop  → Her zaman başarılı, zorla durdur
POST /api/config      → {language?, task?, correction_enabled?}
GET  /api/devices     → Ses girişi cihazları
```

### Kritik Implementation Detayları
- **MLX thread safety:** `ThreadPoolExecutor(max_workers=1)` — Metal GPU tek thread
- **Lazy loading:** Modeller ilk kullanımda yüklenir, startup'ı bloklamaz
- **LLM on-demand:** Correction açıldığında yükle, kapandığında unload (~4GB boşalt)
- **Metal cache:** Her inference sonrası `mx.metal.clear_cache()` — bellek sızıntısı önler
- **Ses format:** 16kHz, mono, float32 (Whisper standardı)
- **Log dosyası:** `/tmp/voiceflow.log`

### TranscriptionResponse (Doğrulanmış)
```python
{
    "text": "Bugün hava çok güzel.",      # Final metin (düzeltilmişse)
    "raw_text": "bugun hava cok guzel",   # Sadece düzeltildiyse dolu
    "corrected": true,
    "language": "tr",
    "duration": 3.45                       # Ses süresi (saniye)
}
```

### Mevcut Modeller
- **Whisper:** `mlx-community/whisper-small-mlx` (~500MB, HuggingFace cache)
- **LLM:** `mlx-community/Qwen2.5-7B-Instruct-4bit` (~4GB, HuggingFace cache)
- **Correction prompt:** ASCII Türkçe → düzgün Türkçe (ç,ş,ğ,ı,ö,ü)
- **Decoding:** greedy (temp=0), max 512 token, 1.5x uzunluk güvenlik sınırı

---

## Hedef Backend (v1.0, Server Modu)

### Yeni Özellikler Gerekiyor

#### 1. Configurable Server URL
Şu an `host="127.0.0.1"` hardcoded. Server modunda:
```python
# main.py
uvicorn.run(app, host="0.0.0.0", port=8765)
```

#### 2. Auth Middleware
```python
# api/auth.py
async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key not in VALID_KEYS:
        raise HTTPException(status_code=401)
```

#### 3. NVIDIA GPU Desteği (MLX → CUDA)
Local modda MLX kalır. Server modunda:
```
mlx-whisper    →  faster-whisper (NVIDIA CUDA)
mlx-lm         →  Ollama (OpenAI-compatible API)
```

Ortam değişkeniyle seçilir:
```bash
BACKEND_MODE=server        # veya local
LLM_ENDPOINT=http://ollama:11434  # Ollama base URL
```

#### 4. faster-whisper Entegrasyonu — ÖNEMLİ DETAY

faster-whisper **numpy array almıyor** — file path veya file-like object istiyor.
Mevcut AudioCapture numpy array döndürüyor. Adapter gerekli:

```python
# transcription/faster_whisper_transcriber.py
import io
import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel

model = WhisperModel("large-v3", device="cuda", compute_type="float16")

def transcribe(audio: np.ndarray, sample_rate: int = 16000):
    # numpy array → BytesIO (WAV format)
    buf = io.BytesIO()
    sf.write(buf, audio, sample_rate, format="WAV")
    buf.seek(0)

    segments, info = model.transcribe(
        buf,
        language="tr",          # None = auto-detect
        vad_filter=True,        # Sessizlikleri filtrele
        beam_size=5,
    )
    text = " ".join(s.text for s in segments).strip()
    return text, info.language
```

```python
# Dil tespiti için ayrı metod (transkripsiyon yapmadan):
language, probability, _ = model.detect_language(audio_path)
```

Batched pipeline (çok kullanıcı için, Phase 1+):
```python
from faster_whisper import WhisperModel, BatchedInferencePipeline
model = WhisperModel("large-v3", device="cuda", compute_type="float16")
batched_model = BatchedInferencePipeline(model=model)
segments, info = batched_model.transcribe(buf, batch_size=16)
```

#### 5. Ollama LLM Entegrasyonu — Birleşik Client

**Kritik Bulgu:** mlx-lm de OpenAI-compatible HTTP server sunuyor (`mlx_lm.server`).
Ollama da `/v1/chat/completions` endpoint'i sunuyor.
→ **Tek HTTP client, her iki mod için çalışır.**

```python
# correction/llm_corrector.py (server mode)
import httpx

async def correct(text: str, llm_endpoint: str) -> str:
    response = await httpx.AsyncClient().post(
        f"{llm_endpoint}/v1/chat/completions",
        json={
            "model": "qwen2.5:7b",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                *FEW_SHOT_EXAMPLES,
                {"role": "user", "content": text},
            ],
            "temperature": 0.0,   # Greedy decoding
            "max_tokens": 512,
            "stream": False,
        },
        timeout=30.0,
    )
    return response.json()["choices"][0]["message"]["content"]
```

Ollama `keep_alive` parametresi ile model GPU'da kalır (cold start yok):
```python
# Ollama-specific: modeli sürekli yüklü tut
await client.post(f"{endpoint}/api/generate", json={
    "model": "qwen2.5:7b",
    "keep_alive": -1   # Sonsuza kadar yüklü tut
})
```

#### 4. Context Engine (RAG)
Şu an yok. Eklenecek:

```
backend/src/voiceflow/
└── context/
    ├── embedder.py      # Metin → vektör (local embedding model)
    ├── store.py         # ChromaDB CRUD
    ├── retriever.py     # Query → top-K chunks
    └── ingestion.py     # Dosya/klasör → parse → embed → store
```

**Seçilen stack:**
- Vector DB: ChromaDB (embedded, Python, Docker'da kolay)
- Embedding: `sentence-transformers/all-MiniLM-L6-v2` veya MLX muadili

#### 5. Kullanıcı Profili ve Multi-User
```python
class UserProfile(BaseModel):
    user_id: str
    name: str
    role: str          # "engineer" | "manager" | "sales"
    department: str
    language: str      # "tr" | "en"
    mode: str          # "engineering" | "office" | "general"
```

Her `/api/stop` isteğine `user_id` eklenir → kişiye özel context retrieval.

#### 6. Persistent Storage
Şu an history sadece RAM'de (uygulama kapanınca siler).

```
SQLite:
├── transcriptions (id, user_id, text, raw_text, language, ts, duration)
├── user_profiles  (user_id, name, role, department, mode)
└── knowledge_chunks (id, user_id, source, content, embedding_id, ts)
```

#### 7. Audit Log
Her request loglanır:
```python
{
    "ts": "2024-01-15T09:23:11",
    "user_id": "talha@akbank.com",
    "action": "transcribe",
    "duration_sec": 4.2,
    "processing_ms": 1150,
    "language": "tr",
    "corrected": true
}
```

---

## Docker Compose (Server Deployment)

```yaml
# docker-compose.yml
services:
  voiceflow-api:
    build: ./backend
    ports: ["8765:8765"]
    environment:
      - BACKEND_MODE=server
      - LLM_ENDPOINT=http://ollama:11434
      - API_KEYS=key1,key2
    volumes:
      - ./data:/data  # SQLite + ChromaDB

  ollama:
    image: ollama/ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    volumes:
      - ollama_models:/root/.ollama

  faster-whisper:
    image: fedirz/faster-whisper-server:latest-cuda
    environment:
      - WHISPER__MODEL=large-v3
```

---

## Hız Karşılaştırması (Doğrulanmış Sayılar)

| Ortam | Whisper | LLM (7B) | Toplam |
|---|---|---|---|
| Mac M1/M2 local (LLM kapalı) | ~0.3–0.5s | — | ~0.5s |
| Mac M1/M2 local (LLM açık) | ~0.3–0.5s | ~3–4s | ~3.5–4.5s |
| RTX 4090 server (LAN) | ~0.2–0.3s | ~0.5–1s | ~0.8–1.3s |
| RunPod RTX 4090 (internet) | ~0.2–0.3s | ~0.5–1s | ~1–1.5s |

---

## Bağımlılıklar

### Mevcut (pyproject.toml)
```toml
mlx-whisper>=0.4.0
mlx-lm>=0.21.0
sounddevice>=0.5.0
fastapi>=0.109.0
uvicorn>=0.27.0
numpy>=1.24.0
```

### Server Modu İçin Eklenecek
```toml
faster-whisper>=1.1.0   # NVIDIA Whisper (numpy array değil BytesIO!)
soundfile>=0.12.0       # numpy → WAV dönüşümü için (faster-whisper adapter)
chromadb>=0.5.0         # Vector store (multi-tenant: tenant+database params)
sentence-transformers   # Embedding
python-jose             # JWT auth
sqlalchemy>=2.0         # SQLite ORM
httpx>=0.27.0           # Async Ollama/mlx-lm OpenAI-compat client
ollama>=0.3.0           # Ollama Python client (opsiyonel, httpx yeterli)
```
