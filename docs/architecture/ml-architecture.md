# ML Architecture

VoiceFlow iki ayrı fine-tuned model kullanır: Whisper (ASR) + Qwen (correction).

```
Mikrofon → Whisper (voiceflow-whisper-tr-v2) → ham metin → Qwen + qwen-adapter → düzeltilmiş metin
```

## İki Adapter Mimarisi

| | Whisper | Qwen Adapter |
|---|---|---|
| **Base model** | `openai/whisper-large-v3-turbo` | `Qwen2.5-7B-Instruct-4bit` |
| **Fine-tune hedefi** | Türkçe akustik + noktalama/büyük harf | ASR hatası düzeltme |
| **Eğitim verisi** | ISSAI 164K pair (2 stage) | 244K sentetik/gerçek pair |
| **Format** | Merge → MLX float16 | HF PEFT → MLX |
| **Aktif model** | `voiceflow-whisper-tr` (v1, production) | `adapters_mlx/adapters.safetensors` |
| **Sonraki model** | `voiceflow-whisper-tr-v2` (Stage 2 eğitimde) | — |
| **Boyut** | 1.5GB MLX float16 | ~39MB adapter |

Detay: `docs/ml/two-adapter-architecture.md`

---

## Whisper Eğitim Stratejisi (2-Stage)

### Stage 1 — Genel Türkçe ASR (TAMAMLANDI ✓)
- **Veri:** ISSAI 164K WAV+text pair
- **Config:** LoRA r=16, LR=1e-3, 3 epoch, batch=16
- **Süre:** ~4.6 saat H100
- **Çıktı:** `tkosen/voiceflow-whisper-tr` (HF) + `ml/whisper/models/voiceflow-whisper-tr-mlx/` (lokal)
- **Sorun:** Eğitim verisindeki `.txt` dosyaları lowercase, noktalama yok → model düz metin üretiyor

### Stage 2 — Noktalama/Büyük Harf (HAZIRLANIYOR)
- **Motivasyon:** Stage 1 çıktısı akustik olarak doğru ama büyük harf/noktalama yok
- **Veri hazırlık:** `issai_punctuated.jsonl` (164K satır, Claude Haiku ile noktalama eklendi)
  - 83 shard × 2000 satır → paralel agent işlemi → merge
  - 60.9% satırda değişiklik; Türkçe i→İ, ı→I kuralları dahil
- **Config:** Base=voiceflow-whisper-tr, LoRA r=8, **LR=5e-6** (catastrophic forgetting önle), 2 epoch, batch=32
- **Çıktı:** `voiceflow-whisper-tr-v2`

### Stage 2 RunPod Optimizasyon Stratejisi

| Faktör | Stage 1 | Stage 2 |
|---|---|---|
| Epoch | 3 | **2** |
| Batch | 16 | **32** |
| Workers | 8 | **16** |
| torch.compile | ✗ | **✓ (+20%)** |
| Adam | default | **adamw_bnb_8bit** |
| prefetch_factor | ✗ | **4** |
| RAM disk (`/dev/shm`) | ✗ | **✓ (I/O kaldırır)** |

**Tahmini süre: ~2 saat (~$8 @ H100)**

RAM disk trick: ISSAI WAV'lar ~26GB, H100 pod RAM 200GB+ → WAV'ları `/dev/shm/`'e kopyala, disk I/O sıfırla.

RunPod: `python runpod/create_pod.py stage2`

---

## Dizin Yapısı

### `ml/`

```
ml/
├── qwen/                           # LLM correction fine-tuning
│   ├── scripts/
│   │   ├── train_runpod.py         # RunPod Unsloth + TRL eğitim
│   │   ├── prepare_dataset.py      # JSONL birleştir → train/valid/test split
│   │   ├── evaluate.py             # WER, CER, exact-match metrics
│   │   ├── convert_adapter.py      # HF PEFT → MLX format dönüşüm
│   │   └── lora_config.yaml        # MLX LoRA config (rank=8, lr=1e-5)
│   ├── generators/
│   │   ├── corruption_pipeline.py  # Sentetik Whisper hata üretimi (3K pair)
│   │   ├── claude_generator.py     # Claude API ile gerçekçi pair üretimi (1K)
│   │   ├── whisper_loop.py         # TTS → Whisper → gerçek hata pair'i
│   │   ├── word_order_generator.py # Türkçe kelime sırası düzeltme pair'leri
│   │   └── domain_generator.py     # Proje bazlı domain pair üretimi
│   ├── data/                       # Ham üretilmiş pair'ler (JSONL)
│   ├── datasets/                   # Hazır eğitim seti (244K train, 30K valid/test)
│   └── adapters_mlx/
│       ├── adapters.safetensors    # MLX format — production'da kullanılan
│       ├── adapter_config.json
│       └── raw/                    # RunPod çıktısı (HF PEFT format)
│
└── whisper/                        # ASR fine-tuning
    ├── whisper_issai_finetune.py   # Stage 1: ISSAI 164K (H100, LoRA r=16, 3 epoch)
    ├── whisper_stage2_finetune.py  # Stage 2: noktalama (H100, LoRA r=8, LR=5e-6, 2 epoch)
    ├── whisper_poc_finetune.py     # Mac'te whisper-small PoC (IT dataset)
    ├── scripts/
    │   ├── punctuate_issai.py      # ISSAI text → Claude Haiku ile noktalama ekleme
    │   └── convert_whisper_mlx.py  # HF safetensors → MLX float16 dönüşüm
    ├── generators/
    │   ├── persona_terms.py        # 8 IT persona + teknik terim listesi
    │   ├── sentence_generator.py   # Qwen ile IT cümle üretimi
    │   └── tts_generator.py        # TTS: cümle → WAV
    ├── datasets/
    │   ├── issai/
    │   │   ├── issai_pairs_clean.jsonl     # 164K ham pair (ISSAI → faster-whisper)
    │   │   ├── issai_punctuated.jsonl      # 164K noktalı pair (Stage 2 eğitim verisi)
    │   │   └── shards/                     # 83 × 2000 satır shard (işlem sırasında)
    │   └── it_dataset/
    │       ├── whisper_sentences.jsonl     # Üretilmiş IT cümleleri (~4.5K)
    │       └── recordings/                 # Uygulama üzerinden kaydedilen WAV'lar
    ├── models/
    │   ├── voiceflow-whisper-tr-mlx/       # Aktif model (Stage 1, MLX float16, 1.5GB)
    │   └── voiceflow-whisper-tr-v2-mlx/    # Stage 2 sonrası (henüz eğitimde)
    └── whisper_poc_adapter/                # whisper-small PoC checkpoint
```

---

## Eğitim Pipeline'ları

### Qwen Adapter Eğitimi

```
1. Veri üretimi
   generators/ → data/*.jsonl (3K–5K pair/generator)

2. Dataset hazırlama
   prepare_dataset.py → datasets/train.jsonl (244K), valid.jsonl, test.jsonl

3. RunPod eğitimi
   train_runpod.py → /workspace/adapters/ (HF PEFT, RTX 4090, ~8 saat)

4. Format dönüşüm
   convert_adapter.py → adapters_mlx/adapters.safetensors (MLX, ~39MB)

5. Deploy
   config.yaml: llm.adapter_path: ml/qwen/adapters_mlx
```

### Whisper Eğitimi (2-Stage)

```
Stage 1 — Genel Türkçe (TAMAMLANDI)
   issai_pairs_clean.jsonl (164K)
   ↓
   whisper_issai_finetune.py → voiceflow-whisper-tr (H100, ~4.6 saat)
   ↓
   convert_whisper_mlx.py → voiceflow-whisper-tr-mlx (float16, 1.5GB)
   ↓ PRODUCTION (config.yaml: whisper.model)

Stage 2 — Noktalama/Büyük Harf
   issai_pairs_clean.jsonl → punctuate_issai.py (Claude Haiku, 83 paralel agent)
   ↓
   issai_punctuated.jsonl (164K, 60.9% değişiklik)
   ↓
   whisper_stage2_finetune.py → voiceflow-whisper-tr-v2 (H100, ~2 saat)
   ↓
   convert_whisper_mlx.py → voiceflow-whisper-tr-v2-mlx

Stage 3 — IT Domain (planlı)
   sentence_generator.py + tts_generator.py → it_dataset/*.wav
   + Uygulama kayıt ekranı
   → voiceflow-whisper-it
```

---

## Config Referansı

```yaml
# config.yaml
whisper:
  model: ml/whisper/models/voiceflow-whisper-tr-mlx   # merge edilmiş model (adapter değil)

llm:
  adapter_path: ml/qwen/adapters_mlx                  # Qwen LoRA (MLX format)
```

Secrets (API key, token) → `.env` | Model/path → `config.yaml`
