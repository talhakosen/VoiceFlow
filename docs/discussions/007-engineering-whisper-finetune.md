# 007 — Engineering Whisper: Türkiye IT Sektörüne Özel ASR

Engineering mode için kendi Whisper'ımızı eğitiyoruz.
Hedef: "Kubernetes deploy ettim" → Whisper direkt doğru yazsın, LLM corrector'a gerek kalmasın.

---

## Neden

Mevcut sorun:
- Whisper "Docker" → "doker", "Flutter" → "flatter", "Kubernetes" → "kübernetis"
- LLM corrector düzeltiyor ama: +1-3 saniye gecikme, hata payı var
- Türkiye IT konuşması = İngilizce terimler + Türkçe cümle yapısı → eğitim datasında neredeyse yok

Hedef:
- Whisper direkt "Docker", "Flutter", "Kubernetes" yazsın
- Engineering mode → fine-tuned Whisper yükle
- LLM correction IT terimleri için gereksiz hale gelir

---

## Persona & Vocabulary Sistemi

Her persona = teknik terim listesi + Türkçe telaffuz varyantları

### Personalar

| Persona | Terimler (örnek) |
|---|---|
| Backend Dev | Spring Boot, microservice, endpoint, middleware, Kafka, Redis, JWT, OAuth, CRUD, ORM |
| Frontend Dev | React, TypeScript, Webpack, npm, hook, props, Redux, Tailwind, responsive, component |
| Flutter Dev | Flutter, Dart, widget, setState, BLoC, Riverpod, pubspec, Navigator, BuildContext |
| .NET Dev | C#, ASP.NET, Entity Framework, LINQ, NuGet, dependency injection, Blazor, SignalR |
| Mobile Dev | Swift, Kotlin, Xcode, CocoaPods, Gradle, ADB, simulator, provisioning profile |
| DevOps | CI/CD, Jenkins, GitHub Actions, Terraform, Helm, Kubernetes, Dockerfile, pod, namespace |
| Junior Dev | Git, commit, push, pull, merge, branch, PR, code review, issue, fork |
| Data/ML | pandas, numpy, PyTorch, model, training, loss, epoch, batch, embedding, fine-tune |

### Telaffuz Varyantları (Örnek)

| Doğru | Türkçe Telaffuz Varyantı |
|---|---|
| Kubernetes | kübernetis, kubernetis, k8s (ke sekiz es) |
| Docker | doker, dökır |
| Flutter | flatter, flötür, fılatter |
| TypeScript | tayp skript, tayp eskript |
| GraphQL | grafikul, graf kul, graf küel |
| npm | en pi em, en pem |
| API | a pi i, eypiai |
| JWT | ce double-u ti, jay double-u ti, jeydubbti |
| Redux | ridaks, rıdaks |
| Webpack | vebpak, uebpak |
| GitHub | git hab, githab |
| CI/CD | si ai si di, siyay siydi |

---

## Veri Üretim Pipeline

```
Opus (metin kalitesi)
    ↓
Cümle üretimi (persona × senaryo × yoğunluk)
    ↓
TTS → WAV (macOS say / Edge TTS)
    ↓
Augmentasyon (hız × gürültü × oda)
    ↓
(audio, ground_truth) çiftleri
    ↓
Whisper fine-tune (RunPod RTX 4090)
```

### Adım 1: Cümle Üretimi (Opus)

Opus'a persona + senaryo veriyoruz, doğal Türkçe cümleler üretiyor:

```
Senaryo tipleri:
- standup: "Bugün X üzerinde çalışıyorum, Y'yi deploy ettim"
- code review: "Bu endpoint'te N+1 problemi var, index ekleyelim"
- hata ayıklama: "Kubernetes pod'ları CrashLoopBackOff veriyor"
- planlama: "Önce Docker image'ı optimize edelim, sonra CI/CD pipeline kurarız"
- sohbet: "React hook'larına geçince Redux'ı kaldırdık, çok daha temiz oldu"
```

Hedef:
- 10 persona × 50 senaryo × 3 yoğunluk (az/orta/yoğun teknik) = **1500 cümle**
- Opus maliyeti: ~$3-5

### Adım 2: TTS → WAV

```python
# macOS say (Türkçe sesler)
os.system(f'say -v Yelda -r {rate} "{text}" -o {output}.aiff')
# aiff → wav (16kHz, mono)

# Sesler: Yelda, Meltem (Türkçe)
# Hızlar: 150, 180, 210, 250 kelime/dk
```

Edge TTS alternatif (daha doğal):
- `tr-TR-EmelNeural` (kadın)
- `tr-TR-AhmetNeural` (erkek)

### Adım 3: Augmentasyon

```python
augmentations = [
    {"speed": 0.9},    # yavaş konuşan
    {"speed": 1.0},    # normal
    {"speed": 1.2},    # hızlı
    {"speed": 1.5},    # çok hızlı
    {"noise_snr": 20}, # hafif gürültü (ofis)
    {"noise_snr": 10}, # orta gürültü
    {"noise_snr": 5},  # gürültülü ortam
]
```

1500 cümle × 2 ses × 4 hız × 2 gürültü = **~24.000 WAV** (≈15-20 saat ses)

### Adım 4: ISSAI Birleştirme

Mevcut: 164K gerçek Türkçe konuşma çifti (domain-agnostic)
Yeni: 24K IT-domain sentetik çift

Oran: 70% ISSAI + 30% IT sentetik = **domain bilgisi kazanır, Türkçe unutmaz**

---

## Whisper Fine-Tuning

### Model Seçimi

| Model | Boyut | Fine-tune Süresi | Deploy |
|---|---|---|---|
| whisper-small | 244M | ~2 saat | mlx hızlı |
| whisper-medium | 769M | ~6 saat | mlx orta |
| whisper-large-v3-turbo | ~800M | ~10 saat | **mevcut model** |

**Karar:** whisper-large-v3-turbo üzerine LoRA — mevcut MLX modeli korunur, sadece adapter eklenir.

### LoRA Config (Whisper Encoder)

```python
# Whisper encoder attention layer'larına LoRA
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "v_proj"],
    lora_dropout=0.05,
    task_type="SEQ_2_SEQ_LM",
)
```

### Training (RunPod RTX 4090)

```bash
# HuggingFace Trainer
python whisper_finetune.py \
    --model openai/whisper-large-v3-turbo \
    --train_data it_turkish_train.jsonl \
    --eval_data it_turkish_valid.jsonl \
    --output_dir adapters/whisper_it_v1 \
    --max_steps 5000 \
    --learning_rate 1e-4
```

### Deployment

```python
# Engineering mode:
WHISPER_MODEL = "mlx-community/whisper-large-v3-turbo"
WHISPER_ADAPTER = "scripts/training/whisper_adapters/it_v1"

# Diğer modlar: base model (adapter yok)
```

---

## Script Yapısı

```
backend/scripts/data_gen/
├── persona_terms.py          # Persona vocabulary + telaffuz varyantları
├── sentence_generator.py     # Opus API → cümle üretimi
├── tts_generator.py          # Metin → WAV (macOS say / Edge TTS)
├── audio_augment.py          # Hız + gürültü augmentasyonu
└── build_whisper_dataset.py  # Tüm pipeline orchestration

backend/scripts/training/
├── whisper_finetune.py       # HuggingFace LoRA fine-tune
├── whisper_evaluate.py       # WER + IT term accuracy
└── convert_whisper_mlx.py    # HF adapter → MLX format
```

---

## Başarı Kriterleri

| Metrik | Hedef |
|---|---|
| IT term WER (fine-tuned) | < %5 (mevcut > %30) |
| Genel Türkçe WER | base modelden %2'den fazla kötüleşme yok |
| "Docker" → "Docker" | %98+ doğruluk |
| "Kubernetes" → "Kubernetes" | %95+ doğruluk |

---

## Faz Planı

| Faz | İş | Süre |
|---|---|---|
| P1 | `persona_terms.py` — 8 persona × terim listesi + telaffuz | 4 saat |
| P1 | `sentence_generator.py` — Opus API, 1500 cümle üret | 2 saat + $5 API |
| P1 | `tts_generator.py` — macOS say / Edge TTS → WAV | 3 saat |
| P2 | `audio_augment.py` — hız + gürültü, 24K WAV | 2 saat |
| P2 | `build_whisper_dataset.py` — ISSAI + IT sentetik birleştir | 2 saat |
| P3 | `whisper_finetune.py` — RunPod LoRA fine-tune | 1 gün |
| P3 | `convert_whisper_mlx.py` — MLX deploy + engineering mode entegrasyon | 4 saat |

---

## Neden Değerli

- **Whisper direkt doğru yazar** — "Kubernetes" → "Kubernetes", sıfır post-processing
- **Engineering mode farkı** — rakipte yok, Türkiye IT'sine özgü
- **Veri makineden çıkmaz** — synthetic generation, KVKK sorunu yok
- **Büyüyebilir** — müşteri jargonu eklenince adapter üstüne adapter fine-tune
