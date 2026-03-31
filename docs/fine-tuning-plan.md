# VoiceFlow — Fine-Tuned Correction Model Planı

> Tarih: 31 Mart 2026
> Amaç: Wispr Flow kalitesinde correction — filler removal, backtracking, Turkish char fix, punctuation
> Hedef Model: Qwen2.5-7B-Instruct üzerine LoRA fine-tune (MLX)

---

## 1. Neden Fine-Tune?

**Mevcut durum:** Generic Qwen 7B + uzun system prompt + few-shot examples
- Backtracking (yarın hayır cuma) güvenilir çalışmıyor
- Filler removal bazen içeriği de siliyor
- Turkish char fix inconsistent
- Prompt her request'te ~500 token overhead

**Fine-tune sonrası:**
- Davranışlar modele gömülü — prompt kısa ve güvenilir
- Backtracking/filler/punctuation pattern'ları öğrenilmiş
- Latency düşer (kısa prompt = daha az input token)
- Türkçe'ye özel correction kalitesi dramatik artar

**Wispr Flow bunu yapıyor:** Llama 3.1 fine-tune, <250ms inference, production'da.

---

## 2. Pipeline Genel Bakış

```
Phase 1: Veri Toplama (3-5 gün)
  ├── Clean text corpus (10K cümle)
  ├── Corruption pipeline (Python)
  ├── Synthetic pairs (4K)
  ├── LLM-generated pairs (1K)
  └── Whisper-in-the-loop pairs (300-500)

Phase 2: Fine-Tuning (1-2 gün)
  ├── Data formatting (chat template)
  ├── LoRA training (MLX)
  └── Evaluation (held-out test set)

Phase 3: Entegrasyon (1 gün)
  ├── Model swap (mlx-lm load adapter)
  ├── Prompt simplification
  └── A/B test (fine-tuned vs prompt-only)
```

---

## 3. Phase 1: Veri Toplama

### 3.1 Clean Text Corpus (10K cümle)

Kaynaklar:
- **Mozilla Common Voice TR**: ~100+ saat validated Türkçe transkript
- **Wikipedia TR**: Genel, teknik, iş dünyası cümleleri
- **Şirket içi dokümanlar**: Gerçek kurumsal jargon (opsiyonel, müşteriye özel)
- **Mevcut VoiceFlow transcription history**: `~/.voiceflow/voiceflow.db`

Domain dağılımı:
```
4,000  Genel (günlük konuşma, iş)
3,000  Teknik (yazılım, engineering)
2,000  Ofis/kurumsal (email, toplantı)
1,000  Mixed (Türkçe-İngilizce code-switch)
```

### 3.2 Corruption Pipeline (Python)

```python
# backend/scripts/generate_training_data.py

import random

TURKISH_CHAR_MAP = {
    'ç': 'c', 'Ç': 'C', 'ğ': 'g', 'Ğ': 'G',
    'ı': 'i', 'İ': 'I', 'ö': 'o', 'Ö': 'O',
    'ş': 's', 'Ş': 'S', 'ü': 'u', 'Ü': 'U',
}

TR_FILLERS = ["yani", "şey", "hani", "işte", "ee", "aa", "aslında", "mesela"]
EN_FILLERS = ["um", "uh", "like", "you know", "basically", "so"]

BACKTRACK_PATTERNS = [
    ("hayır {new}", "actually {new}", "yok yok {new}"),
    ("{old} değil {new}", "{old} hayır {new} demek istiyorum"),
    ("{old} pardon {new}"),
]

TECH_MISHEARINGS = {
    "Kubernetes": ["kubernetis", "kubernets"],
    "PostgreSQL": ["postgre siküel", "post gres"],
    "AppViewModel": ["apvyumodel", "app view model"],
    "deployment": ["diployment", "deploy ment"],
    "authentication": ["otantikasyon", "otentikeyşın"],
    "microservice": ["mikro servis", "maykro servis"],
}

def corrupt_turkish_chars(text: str, rate: float = 0.5) -> str:
    """Randomly remove Turkish special characters."""
    result = []
    for char in text:
        if char in TURKISH_CHAR_MAP and random.random() < rate:
            result.append(TURKISH_CHAR_MAP[char])
        else:
            result.append(char)
    return "".join(result)

def inject_fillers(text: str, count: int = 2) -> str:
    """Insert filler words at random positions."""
    words = text.split()
    fillers = TR_FILLERS if any(c in text for c in 'çğışöüÇĞİŞÖÜ') else EN_FILLERS
    for _ in range(count):
        pos = random.randint(0, len(words))
        words.insert(pos, random.choice(fillers))
    return " ".join(words)

def remove_punctuation(text: str) -> str:
    """Strip all punctuation (Whisper often misses it)."""
    return text.replace(".", "").replace(",", "").replace("?", "").replace("!", "").replace(":", "").replace(";", "")

def inject_backtracking(text: str) -> str:
    """Add a self-correction somewhere in the sentence."""
    words = text.split()
    if len(words) < 4:
        return text
    pos = random.randint(1, len(words) - 2)
    original_word = words[pos]
    # Insert a fake word then correction
    fake_word = random.choice(["pazartesi", "salı", "yarın", "bugün", "şimdi"])
    correction = random.choice(["hayır", "yok", "pardon", "yani"])
    words.insert(pos, f"{fake_word} {correction}")
    return " ".join(words)

def apply_corruptions(clean_text: str, difficulty: str = "medium") -> str:
    """Apply stacked corruptions based on difficulty."""
    text = clean_text
    
    if difficulty == "easy":  # Single corruption
        corruption = random.choice([corrupt_turkish_chars, inject_fillers, remove_punctuation])
        text = corruption(text)
    elif difficulty == "medium":  # 2 corruptions
        text = remove_punctuation(text)
        text = random.choice([corrupt_turkish_chars, inject_fillers])(text)
    elif difficulty == "hard":  # 3+ corruptions
        text = remove_punctuation(text)
        text = corrupt_turkish_chars(text)
        text = inject_fillers(text)
        if random.random() > 0.5:
            text = inject_backtracking(text)
    
    return text.lower()  # Whisper often outputs lowercase
```

### 3.3 Veri Dağılımı (5,000 pair hedef)

```
1,500  Turkish char fix only (en kolay ama iyi represent edilmeli)
1,000  Filler removal + punctuation
  800  Backtracking/self-correction
  700  Mixed errors (2-3 error tipi birlikte)
  500  Technical term correction
  300  Code-switching (Türkçe/İngilizce karışık)
  200  Edge case (çok kısa, çok uzun, sayılar, tarihler)
```

### 3.4 LLM ile Synthetic Generation (1,000 pair)

Claude/GPT-4'e prompt:
```
Generate 10 pairs of (raw_whisper_transcript, corrected_text) for a 
Turkish software engineer dictating in a {context} context.

Each pair should contain different error types from:
- Turkish character errors (ç→c, ş→s, ğ→g, ı→i, ö→o, ü→u)
- Filler words (yani, şey, hani, işte, ee, aa)
- Self-corrections/backtracking (yarın hayır cuma)
- Missing punctuation
- Technical term misrecognition

Format as JSON:
[{"raw": "...", "corrected": "..."}, ...]
```

### 3.5 Whisper-in-the-Loop (300-500 pair)

En gerçekçi veri — asıl Whisper hatalarını yakalar:
1. Clean text'ten TTS ile ses üret (Coqui TTS Turkish veya macOS `say`)
2. Whisper'dan geçir → gerçek hataları yakala
3. Manuel düzelt

```bash
# macOS TTS ile basit yaklaşım
say -v Yelda -o sample.aiff "Toplantı saat üçte başlıyor"
# Whisper'dan geçir
python -c "
import mlx_whisper
result = mlx_whisper.transcribe('sample.aiff', language='tr')
print(result['text'])
"
```

---

## 4. Phase 2: Fine-Tuning

### 4.1 Veri Formatı (Chat Template)

```jsonl
{"messages": [
  {"role": "system", "content": "You are a speech-to-text post-processor. Fix the raw transcript: correct Turkish characters, remove fillers, handle self-corrections, add punctuation. Output ONLY the corrected text."},
  {"role": "user", "content": "bugun yani toplanti saat uc te basliyo hani hazir ol lutfen"},
  {"role": "assistant", "content": "Bugün toplantı saat üçte başlıyor, hazır ol lütfen."}
]}
{"messages": [
  {"role": "system", "content": "You are a speech-to-text post-processor. Fix the raw transcript: correct Turkish characters, remove fillers, handle self-corrections, add punctuation. Output ONLY the corrected text."},
  {"role": "user", "content": "yarin hayir cuma gunu bulusacagiz ee otelde"},
  {"role": "assistant", "content": "Cuma günü buluşacağız otelde."}
]}
```

Dosya yapısı:
```
backend/data/fine-tune/
  train.jsonl    (4,500 pair — %90)
  valid.jsonl    (500 pair — %10)
  test.jsonl     (held-out, ayrı toplanan)
```

### 4.2 MLX LoRA Fine-Tuning

```bash
# Gereksinimler
pip install "mlx-lm[train]"

# LoRA fine-tune (QLoRA otomatik — 4-bit model kullanıyoruz)
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
  --steps-per-report 10 \
  --steps-per-eval 100 \
  --save-every 200 \
  --adapter-path backend/models/correction-adapter

# OOM olursa --grad-checkpoint ekle (RAM-compute trade-off)
# --batch-size 1 --num-layers 8 --grad-checkpoint

# Test
python -m mlx_lm.lora \
  --model mlx-community/Qwen2.5-7B-Instruct-4bit \
  --adapter-path backend/models/correction-adapter \
  --data backend/data/fine-tune \
  --test

# Interactive test
python -m mlx_lm.generate \
  --model mlx-community/Qwen2.5-7B-Instruct-4bit \
  --adapter-path backend/models/correction-adapter \
  --prompt "bugun toplantida konusacagimiz konular sunlardir"
```

**YAML Config alternatifi** (`backend/finetune/lora_config.yaml`):
```yaml
model: "mlx-community/Qwen2.5-7B-Instruct-4bit"
data: "./backend/data/fine-tune"
fine_tune_type: "lora"
batch_size: 2
num_layers: 16
iters: 1000
learning_rate: 2e-4
mask_prompt: true          # Loss sadece corrected output'ta hesaplanır
save_every: 200
adapter_path: "./backend/models/correction-adapter"
lora_parameters:
  rank: 8
  scale: 20.0              # alpha/rank — efektif ağırlık
  dropout: 0.0
```
```bash
python -m mlx_lm.lora --train --config backend/finetune/lora_config.yaml
```

**Önemli notlar:**
- `--mask-prompt`: Loss sadece assistant (corrected) kısmında hesaplanır — prompt pattern öğrenmez
- QLoRA otomatik: 4-bit model verince base quantized kalır, adapter full precision
- GGUF modeller fine-tune'a uygun DEĞİL — sadece HuggingFace format

**Donanım gereksinimleri:**
| Mac | RAM | Eğitim süresi (1K iter) | Batch size | num-layers |
|-----|-----|------------------------|------------|------------|
| M1/M2 16GB | 16GB | ~25-35 dk | 1 | 8 + grad-checkpoint |
| M2/M3 Pro 18-32GB | 18-32GB | ~15-20 dk | 2 | 16 |
| M3 Max 36GB+ | 36GB+ | ~10-15 dk | 4 | 16 |
| M4 Max 64GB+ | 64GB+ | ~8-12 dk | 4-8 | 16 |

**LoRA Hyperparameters:**
```
rank: 8-16        # 8 ile başla, yetersizse 16'ya çık
scale: 20.0       # alpha/rank oranı
dropout: 0.0      # küçük dataset'te dropout genelde gereksiz
layers: 16        # son 16 layer (Qwen 7B'de 32 layer var)
learning_rate: 2e-4  # LoRA standardı; çok agresifse 1e-4'e düşür
iters: 1000       # val loss izle, düşüyorsa artır
```

### 4.3 Inference (Fine-tuned Model Kullanımı)

```python
from mlx_lm import load, generate

# Base model + adapter yükle
model, tokenizer = load(
    "mlx-community/Qwen2.5-7B-Instruct-4bit",
    adapter_path="backend/models/correction-adapter"
)

# Artık KISA prompt yeterli
messages = [
    {"role": "system", "content": "Fix the raw transcript."},
    {"role": "user", "content": "bugun yani toplanti saat uc te basliyo"}
]

formatted = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
result = generate(model, tokenizer, prompt=formatted, max_tokens=256)
# → "Bugün toplantı saat üçte başlıyor."
```

**Prompt overhead azalması:**
- Mevcut: ~800 token (system + few-shot 5 example)
- Fine-tune sonrası: ~50 token (kısa system prompt)
- **~750 token tasarruf = ~30% latency iyileşme**

### 4.4 Evaluation Metrics

```python
# backend/scripts/evaluate_correction.py

from jiwer import wer, cer  # Word/Character Error Rate

metrics = {
    "WER": wer(reference, hypothesis),      # Word Error Rate
    "CER": cer(reference, hypothesis),      # Character Error Rate — Türkçe char fix için kritik
    "exact_match": reference == hypothesis,  # Tam eşleşme oranı
    "turkish_char_accuracy": ...,           # ç,ş,ğ,ı,ö,ü doğruluk oranı
    "filler_removal_rate": ...,             # Filler'lar ne kadar temizlendi
    "backtrack_accuracy": ...,              # Backtracking doğru mu işlendi
}
```

Hedef metrikler:
| Metric | Mevcut (prompt-only) | Hedef (fine-tune) | Wispr Flow (tahmini) |
|--------|---------------------|-------------------|---------------------|
| WER | ~15% | <5% | <3% |
| CER | ~10% | <3% | <2% |
| Exact match | ~30% | >70% | >80% |
| Turkish char accuracy | ~80% | >98% | N/A (cloud) |
| Filler removal | ~60% | >95% | >95% |
| Backtracking | ~20% | >85% | >90% |

---

## 5. Phase 3: Entegrasyon

### 5.1 LLMCorrector Değişiklikleri

```python
# backend/src/voiceflow/correction/llm_corrector.py

class LLMCorrector:
    def _ensure_model_loaded(self):
        if self._model is None:
            from mlx_lm import load
            
            adapter_path = os.getenv("CORRECTION_ADAPTER_PATH", 
                                      "backend/models/correction-adapter")
            
            if os.path.exists(adapter_path):
                # Fine-tuned model
                self._model, self._tokenizer = load(
                    self.config.model_name,
                    adapter_path=adapter_path
                )
                self._use_short_prompt = True
                logger.info("Loaded fine-tuned correction model")
            else:
                # Fallback: generic model + long prompt
                self._model, self._tokenizer = load(self.config.model_name)
                self._use_short_prompt = False
                logger.info("Loaded generic model (no adapter found)")
```

### 5.2 A/B Test Stratejisi

```
1. Aynı 200 test input'u iki modele gönder
2. Blind review: hangisi daha iyi? (manuel 50 pair)
3. Otomatik metrikler karşılaştır
4. Fine-tune kazanırsa → varsayılan yap
5. Başarısız olursa → prompt-only fallback kalır
```

---

## 6. Server Mode (NVIDIA) + Production Deploy

### 6.1 Fuse: Adapter'ı Base Model'e Göm (Production İçin)

```bash
# Adapter'ı base model ile birleştir → tek model dizini
python -m mlx_lm.fuse \
  --model mlx-community/Qwen2.5-7B-Instruct-4bit \
  --adapter-path backend/models/correction-adapter \
  --save-path backend/models/voiceflow-corrector-v1

# Fused model'i doğrudan yükle (adapter overhead yok)
# model, tokenizer = load("backend/models/voiceflow-corrector-v1")
```

### 6.2 GGUF Export (Ollama / Server Mode)

```bash
# Fuse + GGUF export tek adımda
python -m mlx_lm.fuse \
  --model mlx-community/Qwen2.5-7B-Instruct-4bit \
  --adapter-path backend/models/correction-adapter \
  --save-path backend/models/voiceflow-corrector-v1 \
  --export-gguf

# Ollama Modelfile
cat > backend/models/Modelfile <<'MODELFILE'
FROM backend/models/voiceflow-corrector-v1/voiceflow-corrector-v1.gguf
PARAMETER temperature 0.0
PARAMETER num_predict 512
SYSTEM "Fix the raw transcript: correct Turkish characters, remove fillers, handle self-corrections, add punctuation. Output ONLY the corrected text."
MODELFILE

# Ollama'ya register et
ollama create voiceflow-corrector -f backend/models/Modelfile
```

Bu sayede **tek training workflow** → iki deploy target:
- **Local (Mac):** MLX model + adapter veya fused model
- **Server (NVIDIA):** GGUF → Ollama → OllamaCorrector (mevcut kod değişmez)

---

## 7. İteratif İyileştirme Döngüsü

```
Deploy v1 → Kullanıcı correction'ları topla → 
  Yanlış correction'ları data'ya ekle → 
    Re-train v2 → Deploy v2 → ...
```

**Production data toplama:**
- Her correction sonrası: `(raw, corrected, user_edit)` üçlüsünü SQLite'a kaydet
- Kullanıcı corrected text'i düzenlerse → bu bir eğitim verisi
- Aylık re-train cycle (veya yeterli yeni veri birikince)

Bu, Wispr Flow'un "auto-learn from corrections" özelliğinin altyapısı.

---

## 8. Zaman Çizelgesi

| Hafta | İş | Çıktı |
|-------|-----|-------|
| 1 | Clean text corpus toplama + corruption pipeline | 10K clean + pipeline.py |
| 1-2 | Synthetic data generation (corruption + LLM) | 5K train.jsonl |
| 2 | Whisper-in-the-loop pairs (TTS → Whisper → manual) | 300-500 pair |
| 2-3 | LoRA fine-tune + evaluation | correction-adapter/ |
| 3 | Entegrasyon + A/B test | LLMCorrector güncelleme |
| 3+ | Production data collection loop | İteratif iyileştirme |

**Toplam: ~3 hafta ilk versiyon, sonra sürekli iyileşme.**

---

## 9. Maliyet

| Kalem | Tahmini Maliyet |
|-------|----------------|
| Clean text corpus | Ücretsiz (Common Voice, Wikipedia) |
| LLM synthetic generation (1K pair via Claude) | ~$5-10 API maliyeti |
| TTS → Whisper loop | Ücretsiz (local) |
| Fine-tuning compute | Ücretsiz (kendi Mac'te MLX) |
| Manuel review (500 pair) | ~2-3 saat insan zamanı |
| **Toplam** | **~$10 + 3 hafta geliştirici zamanı** |
