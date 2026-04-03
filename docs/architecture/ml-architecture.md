# ML Architecture

VoiceFlow kullanır iki ayrı fine-tuned model: Whisper (ASR) + Qwen (correction).

```
Mikrofon → Whisper + whisper-adapter → ham metin → Qwen + qwen-adapter → düzeltilmiş metin
```

## İki Adapter Mimarisi

| | Whisper Adapter | Qwen Adapter |
|---|---|---|
| **Base model** | `whisper-large-v3-turbo` | `Qwen2.5-7B-Instruct-4bit` |
| **Fine-tune hedefi** | Türkçe IT terminolojisi doğru tanıma | ASR hatası düzeltme (noktalama, backtracking, kelime sırası) |
| **Eğitim verisi** | ISSAI 164K pair + IT dataset kayıtları | 244K sentetik/gerçek pair |
| **Format** | HF PEFT → MLX | HF PEFT → MLX |
| **Boyut** | ~1.5GB (merge) | ~39MB (adapter) |

Detay: `docs/ml/two-adapter-architecture.md`

---

## Dizin Yapısı

### `ml/`

```
ml/
├── qwen/                         # LLM correction fine-tuning
│   ├── scripts/
│   │   ├── train_runpod.py       # RunPod'da Unsloth + TRL ile eğitim
│   │   ├── prepare_dataset.py    # JSONL birleştir → train/valid/test split
│   │   ├── evaluate.py           # WER, CER, exact-match metrics
│   │   ├── convert_adapter.py    # HF PEFT → MLX format dönüşüm
│   │   └── lora_config.yaml      # MLX LoRA config (rank=8, lr=1e-5)
│   ├── generators/
│   │   ├── corruption_pipeline.py  # Sentetik Whisper hata üretimi (3K pair)
│   │   ├── claude_generator.py     # Claude API ile gerçekçi pair üretimi (1K)
│   │   ├── whisper_loop.py         # TTS → Whisper → gerçek hata pair'i
│   │   ├── word_order_generator.py # Türkçe kelime sırası düzeltme pair'leri
│   │   └── domain_generator.py     # Proje bazlı domain pair üretimi
│   ├── data/                     # Ham üretilmiş pair'ler (JSONL)
│   ├── datasets/                 # Hazır eğitim seti (244K train, 30K valid/test)
│   └── adapters_mlx/
│       ├── adapters.safetensors  # MLX format — production'da kullanılan
│       ├── adapter_config.json
│       └── raw/                  # RunPod çıktısı (HF PEFT format)
│
└── whisper/                      # ASR fine-tuning
    ├── process_issai.py          # ISSAI → faster-whisper → error pair pipeline
    ├── whisper_issai_finetune.py # RunPod H100'de large-v3-turbo fine-tune
    ├── whisper_poc_finetune.py   # Mac'te whisper-small PoC (IT dataset)
    ├── generators/
    │   ├── persona_terms.py      # 8 IT persona + teknik terim listesi
    │   ├── sentence_generator.py # Qwen ile IT cümle üretimi → whisper_sentences.jsonl
    │   └── tts_generator.py      # TTS: cümle → WAV (Edge TTS / OpenAI TTS)
    ├── datasets/
    │   ├── issai/                # ISSAI 164K pair (issai_pairs_*.jsonl)
    │   └── it_dataset/
    │       ├── whisper_sentences.jsonl  # Üretilmiş IT cümleleri (~4.5K)
    │       └── recordings/              # Uygulama üzerinden kaydedilen WAV'lar
    └── whisper_poc_adapter/      # whisper-small PoC checkpoint (checkpoint-38)
```

### `docs/`

```
docs/
├── architecture/
│   ├── architecture.md           # Sistem mimarisi genel bakış (v0.5)
│   ├── app-architecture.md       # Swift MVVM, AppViewModel, build/deploy
│   ├── backend-architecture.md   # FastAPI katman mimarisi, route → service → DB
│   ├── lora-architecture-visual.md  # Pipeline diyagramı (mikrofon → çıktı)
│   └── ml-architecture.md        # Bu dosya — ML pipeline + dizin rehberi
│
├── ml/
│   ├── fine-tuning-plan.md       # Qwen LoRA strateji (backtracking, latency)
│   ├── finetuned-model-security.md  # Adapter dağıtım güvenliği (on-premise vs fused)
│   ├── runpod-finetuning.md      # RunPod kurulum + GPU optimizasyon rehberi
│   ├── turkish-datasets-research.md # Türkçe NLP dataset araştırması
│   └── two-adapter-architecture.md  # İki adapter detay: Whisper + Qwen
│
├── deployment/
│   ├── vscode-integration.md     # VS Code URL scheme entegrasyonu
│   └── runpod-ollama-deployment.md  # RunPod Ollama kurulum rehberi
│
├── enterprise/
│   ├── enterprise-strategy.md    # Ürün vizyonu, Katman roadmap, hedef sektörler
│   ├── research-wispr-flow.md    # Wispr Flow rekabet analizi (teknik + UI/UX)
│   ├── turkey-enterprise-compliance.md  # KVKK, BDDK, ISO 27001 uyumluluk
│   └── turkey-midmarket-sales.md  # Ltd. Şti., e-fatura, yazılım lisansı gereksinimleri
│
└── discussions/
    ├── 001-wispr-flow-correction-pipeline.md  # Wispr reverse-engineering (Baseten, TensorRT)
    ├── 002-fine-tuning-plan.md                # Qwen LoRA problem/çözüm tartışması
    ├── 003-training-mode.md                   # Training Mode UX konsepti
    ├── 004-correction-pipeline-architecture.md # v0.3 vs hedef pipeline karşılaştırması
    ├── 005-training-infrastructure.md         # Mac MLX vs RunPod karar tartışması
    ├── 006-quality-monitor.md                 # Self-improving ASR pipeline konsepti
    └── 007-engineering-whisper-finetune.md    # Engineering mode Whisper fine-tune gerekçesi
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

### Whisper Adapter Eğitimi

```
1. Layer 1 — Genel Türkçe
   process_issai.py → issai_pairs_all.jsonl (164K pair, paralel 3 shard)
   whisper_issai_finetune.py → voiceflow-whisper-tr (H100, ~9 saat)

2. Layer 2 — IT Domain
   sentence_generator.py → whisper_sentences.jsonl (~4.5K cümle)
   tts_generator.py → it_dataset/*.wav (TTS ses üretimi)
   + Uygulama üzerinden el ile kayıt (Ses Eğitimi ekranı)
   whisper_poc_finetune.py → voiceflow-whisper-it

3. Deploy
   config.yaml: whisper.adapter_path: ml/whisper/adapters/akbank_v1
```

---

## Config Referansı

```yaml
# config.yaml
llm:
  adapter_path: ml/qwen/adapters_mlx   # Qwen LoRA (MLX format)

whisper:
  adapter_path: ml/whisper/adapters/akbank_v1  # Whisper LoRA (HF format)
```

Secrets (API key, token) `.env` dosyasında; model/path konfigürasyonu `config.yaml`'da.
