# Fine-Tuned Correction Model Planı

> Tarih: 31 Mart 2026
> Konu: Qwen 7B LoRA fine-tune — veri toplama, eğitim, deploy

---

## Neden Fine-Tune?

**Mevcut:** Generic Qwen 7B + 800 token system prompt + 5 few-shot
**Problem:** Backtracking güvenilmez, filler removal inconsistent, her request'te 800 token overhead

**Fine-tune sonrası:**
- Davranışlar modele gömülü — prompt 50 tokena düşer
- Backtracking/filler/punctuation pattern'ları öğrenilmiş
- ~30% latency iyileşme
- Wispr Flow kalitesi, on-premise

---

## Veri Kaynakları (4 Kanal)

### Kanal 1: Corruption Pipeline (~3,000 pair)

Temiz Türkçe text → simüle edilmiş Whisper hataları:

```python
TURKISH_CHAR_MAP = {
    'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u'
}
TR_FILLERS = ["yani", "şey", "hani", "işte", "ee", "aa"]
BACKTRACK_PATTERNS = ["hayır", "yok", "pardon", "yani X demek istiyorum"]
TECH_MISHEARINGS = {"Kubernetes": "kubernetis", "AppViewModel": "apvyumodel"}
```

3 zorluk seviyesi:
- **Easy:** Sadece Turkish char bozulması
- **Medium:** Char + filler enjeksiyonu
- **Hard:** Char + filler + backtracking + noktalama yok

### Kanal 2: Claude API Generation (~1,000 pair)

Doğal diyalog çiftleri — Claude'a "Türk yazılımcı toplantıda konuşuyor" senaryosu ver.
Daha çeşitli ve doğal hatalar üretir.

### Kanal 3: Whisper-in-the-Loop (~500 pair)

En gerçekçi veri:
```
Clean text → TTS (macOS say -v Yelda) → Whisper → gerçek hatalar → Manuel düzeltme
```

### Kanal 4: Production Feedback (deploy sonrası, sürekli)

Training Mode'dan gelen kullanıcı düzeltmeleri (bkz: 003-training-mode.md)

### Veri Dağılımı (5,000 pair hedef)

```
1,500  Turkish char fix only
1,000  Filler removal + punctuation
  800  Backtracking/self-correction
  700  Mixed errors (2-3 error tipi birlikte)
  500  Technical term correction
  300  Code-switching (Türkçe/İngilizce karışık)
  200  Edge case (çok kısa, çok uzun, sayılar, tarihler)
```

---

## Eğitim (MLX LoRA)

### Veri Formatı

```jsonl
{"messages": [
  {"role": "system", "content": "Fix the raw transcript."},
  {"role": "user", "content": "bugun yani toplanti saat dortte hayir ucte basliyo sey hazir ol"},
  {"role": "assistant", "content": "Bugün toplantı saat üçte başlıyor, hazır ol."}
]}
```

### MLX Komutları

```bash
pip install "mlx-lm[train]"

python -m mlx_lm.lora \
  --model mlx-community/Qwen2.5-7B-Instruct-4bit \
  --data backend/data/fine-tune \
  --train \
  --fine-tune-type lora \
  --batch-size 2 \
  --num-layers 16 \
  --learning-rate 2e-4 \
  --iters 1000 \
  --mask-prompt \
  --save-every 200 \
  --adapter-path backend/models/correction-adapter
```

**Donanım:** Mac M2/M3 Pro'da ~15-20 dakika
**Adapter boyutu:** ~20MB
**`--mask-prompt`:** Loss sadece corrected output'ta hesaplanır

### YAML Config

```yaml
model: "mlx-community/Qwen2.5-7B-Instruct-4bit"
data: "./backend/data/fine-tune"
fine_tune_type: "lora"
batch_size: 2
num_layers: 16
iters: 1000
learning_rate: 2e-4
mask_prompt: true
adapter_path: "./backend/models/correction-adapter"
lora_parameters:
  rank: 8
  scale: 20.0
  dropout: 0.0
```

---

## Deploy

### Local (Mac — MLX)

```python
model, tokenizer = load(
    "mlx-community/Qwen2.5-7B-Instruct-4bit",
    adapter_path="backend/models/correction-adapter"
)
```

### Production (Fused Model)

```bash
python -m mlx_lm.fuse \
  --model mlx-community/Qwen2.5-7B-Instruct-4bit \
  --adapter-path backend/models/correction-adapter \
  --save-path backend/models/voiceflow-corrector-v1
```

### Server (NVIDIA — Ollama)

```bash
python -m mlx_lm.fuse \
  --model ... --adapter-path ... --save-path ... --export-gguf

ollama create voiceflow-corrector -f backend/models/Modelfile
```

Tek training workflow → iki deploy target (MLX + Ollama).

---

## Evaluation Metrikleri

| Metric | Mevcut (prompt-only) | Hedef (fine-tune) |
|--------|---------------------|-------------------|
| WER | ~15% | <5% |
| CER | ~10% | <3% |
| Exact match | ~30% | >70% |
| Turkish char accuracy | ~80% | >98% |
| Filler removal | ~60% | >95% |
| Backtracking | ~20% | >85% |

---

## Müşteriye Özel Adapter (Killer Feature)

```
Base Adapter (VoiceFlow genel)
  ├── Akbank Adapter  (+bankacılık terimleri)
  ├── Turkcell Adapter (+telekom jargonu)
  └── THY Adapter     (+havacılık terimleri)
```

Her müşteri kendi Mac/sunucusunda eğitim yapar — veri hiçbir yere çıkmaz.
Wispr Flow bunu yapamaz (cloud-only, herkes aynı model).

---

## Zaman Çizelgesi

| Hafta | İş |
|-------|-----|
| 1 | Clean text corpus + corruption pipeline |
| 1-2 | Synthetic data generation (4K pair) |
| 2 | Whisper-in-the-loop (500 pair) |
| 2-3 | LoRA fine-tune + evaluation |
| 3 | Entegrasyon + A/B test |
| 3+ | Production feedback loop |

**Toplam: ~3 hafta ilk versiyon, ~$10 maliyet.**
