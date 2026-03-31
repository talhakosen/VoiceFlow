# Training Altyapısı — Nerede, Nasıl Eğitilecek?

> Tarih: 31 Mart 2026
> Konu: Eğitim ortamı seçimi, dosya yapısı, iterasyon döngüsü

---

## Eğitim Ortamı Seçimi

| Seçenek | Avantaj | Dezavantaj | Maliyet |
|---------|---------|------------|---------|
| **Mac (MLX LoRA)** | Sıfır maliyet, hızlı iterasyon, veri çıkmaz | M1 16GB'da sıkışık | $0 |
| **RunPod (NVIDIA)** | Hızlı, büyük batch, büyük model | Veri cloud'a çıkar | ~$1-2/saat |
| **Hibrit** | Data gen local, train RunPod | Karmaşık pipeline | Değişken |

**Karar: Mac (MLX) ile başla.**

Neden:
- 7B 4-bit LoRA = Mac M2/M3 Pro'da 15-20 dk
- Veri makineden çıkmaz → KVKK doğal uyum
- İterasyon çok hızlı: data değiştir → train → 20dk → test
- Enterprise'a satış: "Model sizin Mac'inizde eğitilir"
- RunPod'a geçiş sadece 13B+ model veya 50K+ data için

---

## Dosya Yapısı

```
backend/
├── scripts/
│   ├── data_gen/
│   │   ├── corruption_pipeline.py    ← Clean text → bozuk transcript
│   │   ├── claude_generator.py       ← Claude API ile doğal pair'ler
│   │   ├── whisper_loop.py           ← TTS → Whisper → gerçek hatalar
│   │   └── harvest_feedback.py       ← SQLite'tan user feedback çek
│   │
│   ├── training/
│   │   ├── prepare_dataset.py        ← Tüm kaynakları → train/valid/test.jsonl
│   │   ├── train.sh                  ← mlx_lm.lora wrapper
│   │   ├── evaluate.py               ← WER, CER, exact match
│   │   └── compare_models.py         ← v1 vs v2 A/B karşılaştırma
│   │
│   └── deploy/
│       ├── fuse_model.sh             ← adapter → fused model
│       └── export_gguf.sh            ← fused → GGUF (Ollama)
│
├── data/
│   ├── corpus/                       ← Clean text kaynakları
│   │   ├── common_voice_tr.txt
│   │   ├── wikipedia_tr.txt
│   │   └── custom_sentences.txt
│   │
│   ├── raw_pairs/                    ← Her kanaldan ham pair'ler
│   │   ├── corruption_easy.jsonl
│   │   ├── corruption_medium.jsonl
│   │   ├── corruption_hard.jsonl
│   │   ├── claude_generated.jsonl
│   │   ├── whisper_loop.jsonl
│   │   └── production_feedback.jsonl
│   │
│   └── fine-tune/                    ← MLX'e verilecek final dataset
│       ├── train.jsonl               (4,500 pair)
│       ├── valid.jsonl               (500 pair)
│       └── test.jsonl                (held-out)
│
├── models/
│   ├── correction-adapter/           ← LoRA adapter (~20MB)
│   │   ├── adapters.safetensors
│   │   └── adapter_config.json
│   │
│   └── voiceflow-corrector-v1/       ← Fused model (production)
│
└── finetune/
    └── lora_config.yaml              ← Training hyperparameters
```

---

## Data Flow

```
ADIM 1: CORPUS
common_voice_tr ──┐
wikipedia_tr ─────┤──▶ corpus/ (10K temiz cümle)
custom_sentences ──┘   Filtre: 5-50 kelime, domain tag

ADIM 2: DATA GEN (4 kanal paralel)
corpus/ ──▶ corruption_pipeline.py ──▶ raw_pairs/corruption_*.jsonl (3K)
        ──▶ claude_generator.py   ──▶ raw_pairs/claude_generated.jsonl (1K)
        ──▶ whisper_loop.py       ──▶ raw_pairs/whisper_loop.jsonl (500)
SQLite  ──▶ harvest_feedback.py   ──▶ raw_pairs/production_feedback.jsonl (0→∞)

ADIM 3: PREPARE
raw_pairs/*.jsonl ──▶ prepare_dataset.py ──▶ fine-tune/train.jsonl (90%)
                                         ──▶ fine-tune/valid.jsonl (10%)

ADIM 4: TRAIN
fine-tune/ ──▶ mlx_lm.lora --train ──▶ models/correction-adapter/ (~20dk)

ADIM 5: EVAL
test.jsonl ──▶ evaluate.py ──▶ metrics.json (WER, CER, accuracy)

ADIM 6: DEPLOY
adapter/ ──▶ LLMCorrector (adapter_path=...)  [LOCAL]
         ──▶ fuse → GGUF → Ollama             [SERVER]
```

---

## Training Flywheel (Sürekli İyileşme)

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  DATA     │───▶│ TRAINING │───▶│  EVAL    │───▶│  DEPLOY  │
│ COLLECT   │    │  (MLX)   │    │  (test)  │    │ (adapter) │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
      ▲                                               │
      │           ┌──────────┐                        │
      └───────────│ FEEDBACK │◀───────────────────────┘
                  │(Training │
                  │  Mode)   │
                  └──────────┘
```

### İterasyon Döngüsü

```
Hafta 1-3:  v0 → Synthetic data ile ilk adapter
            Metrik: WER ~8%, backtracking ~70%

Ay 1:       v1 → + 500 production feedback pair
            Metrik: WER ~5%, backtracking ~85%

Ay 3:       v2 → + 2000 feedback + müşteri-specific
            Metrik: WER ~3%, backtracking ~90%

Ay 6+:      v3 → Rakip seviyesi
            Metrik: WER <2%
```

Her iterasyon: data ekle → 20dk train → eval → deploy.

---

## Donanım Gereksinimleri

| Mac | RAM | Eğitim süresi | Batch | Layers |
|-----|-----|---------------|-------|--------|
| M1/M2 16GB | 16GB | ~25-35 dk | 1 | 8 + grad-checkpoint |
| M2/M3 Pro 18-32GB | 18-32GB | ~15-20 dk | 2 | 16 |
| M3 Max 36GB+ | 36GB+ | ~10-15 dk | 4 | 16 |
| M4 Max 64GB+ | 64GB+ | ~8-12 dk | 4-8 | 16 |

OOM olursa: `--grad-checkpoint --batch-size 1 --num-layers 8`

---

## Maliyet Analizi

| Kalem | Maliyet |
|-------|---------|
| Clean text corpus (Common Voice, Wikipedia) | Ücretsiz |
| LLM synthetic generation (1K pair via Claude API) | ~$5-10 |
| TTS → Whisper loop | Ücretsiz (local) |
| Fine-tuning compute | Ücretsiz (Mac MLX) |
| Manuel review (500 pair) | ~2-3 saat |
| **Toplam** | **~$10 + 3 hafta geliştirici zamanı** |
