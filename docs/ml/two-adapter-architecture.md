# VoiceFlow — İki Adapter Mimarisi

VoiceFlow'un ML katmanı iki bağımsız LoRA adapter'dan oluşur.
Birbirini tamamlarlar — çakışmazlar.

---

## Genel Bakış

```
Mikrofon
    ↓
[Whisper base + Whisper Adapter]   ← Adapter 1: sesi doğru metne çevir
    ↓ "Docker kurdum Kubernetes'e deploy ettim"
[Qwen 7B + Qwen Adapter]           ← Adapter 2: metni temizle ve düzelt
    ↓ "Docker kurdum, Kubernetes'e deploy ettim."
Pano
```

---

## Adapter 1 — Whisper Adapter

**Sorumluluk:** Sesi doğru duyma  
**Base model:** openai/whisper-large-v3-turbo (MIT lisans)  
**Adapter boyutu:** ~50-100MB LoRA  
**Eğitim verisi:** (ses dosyası → doğru metin) çiftleri

**Ne öğreniyor:**
- Türk IT konuşucusunun ağzından "doker" sesini duyunca → "Docker" yaz
- "kubernetis" → "Kubernetes", "flatter" → "Flutter", "tayp skript" → "TypeScript"
- Türkçe cümle içindeki İngilizce terimleri doğru tanı

**Neden değerli:**
- Sıfır ek gecikme — zaten Whisper çalışıyor
- Engineering mode'da LLM correction ihtiyacını azaltır
- Rakipte yok (Türkiye IT'ye özel)

**Eğitim kaynağı:**
- 8 IT persona × 1500 Opus-generated cümle → TTS → augmentasyon → ~24K WAV
- + 164K ISSAI gerçek Türkçe (domain unutma önlemi, %70 oran)
- Detay: `docs/discussions/007-engineering-whisper-finetune.md`

**Aktif modlar:** Engineering

---

## Adapter 2 — Qwen Adapter

**Sorumluluk:** Metni temizleme ve düzeltme  
**Base model:** Qwen2.5-7B-Instruct-4bit (Apache 2.0)  
**Adapter boyutu:** ~39MB LoRA  
**Eğitim verisi:** (hatalı metin → doğru metin) çiftleri

**Ne öğreniyor:**
- Filler temizleme: "yani şey işte" → ""
- Noktalama: "gittim eve yemek yedim" → "Gittim eve, yemek yedim."
- Türkçe karakter: "turkce" → "Türkçe"
- Backtracking: "yarın hayır cuma toplantı" → "Cuma toplantı"
- Bağlam uyumu: window title + selected text'e göre ton

**Eğitim kaynağı:**
- corruption_pairs (simüle Whisper hataları)
- GECTurk dataset (71K Türkçe gramer düzeltme)
- word_order_pairs
- Opus-generated diyalog çiftleri
- Detay: `docs/ml/fine-tuning-plan.md`

**Aktif modlar:** General, Office (Engineering'de kapalı)

---

## Mod × Adapter Matrisi

| Mod | Whisper Adapter | Qwen Adapter | Sonuç |
|---|---|---|---|
| Engineering | ✓ (IT terminoloji) | ✗ (kapalı) | Hızlı + doğru IT terimleri |
| General | ✗ (base Whisper) | ✓ (correction açık ise) | Temiz Türkçe |
| Office | ✗ (base Whisper) | ✓ (correction açık ise) | Formal Türkçe |

---

## Deployment

### Genel Kullanıcı (IT Adapter)

```bash
WHISPER_MODEL=voiceflow-whisper-it   # merge edilmiş IT model (~1.5GB)
# WHISPER_ADAPTER_PATH gerekmez
```

### Kurumsal Müşteri (Akbank Örneği)

```yaml
# config.yaml (müşteri instance)
whisper:
  model: voiceflow-whisper-it        # bizim IT-adapted model (müşteriye gönderilir)
  adapter_path: ml/whisper/adapters/akbank_v1  # müşterinin delta adapter'ı (~30MB, on-premise kalır)
```

### Dosya Yapısı

```
ml/
├── qwen/
│   └── adapters_mlx/              ← Qwen adapter (mevcut, canlıda)
│       ├── adapters/
│       └── config.json
└── whisper/
    └── adapters/
        ├── voiceflow-whisper-it/  ← merge edilmiş IT base model
        └── akbank_v1/             ← müşteri delta adapter (sadece 3 dosya)
            ├── adapter_model.safetensors
            ├── adapter_config.json
            └── README.md
```

### Teknik Doğrulama (Test Edildi)

```
whisper-tiny ile kanıtlandı (2026-04-02):

Base Whisper (37,760,640 param)
  + IT LoRA (294,912 trainable — %0.77)
  → merge_and_unload()
  → Merged model: 37,760,640 param ✅ (base ile aynı, normal WhisperModel)
  + Akbank LoRA (147,456 trainable — %0.39)
  → forward pass ✅
  → adapter save: 595KB (sadece delta) ✅
  → adapter reload ✅

Sonuç: voiceflow-whisper-it + akbank_v1 deployment MİMARİSİ DOĞRU.
```

`config.yaml` config:
```yaml
llm:
  adapter_path: ml/qwen/adapters_mlx          # Qwen adapter — şu an aktif
whisper:
  adapter_path: ml/whisper/adapters/akbank_v1  # müşteri adapter'ı (gelecek)
```

---

## Whisper Adapter — Katmanlı Eğitim Mimarisi

Whisper adapter'ı tek seferde eğitilmez. Üç aşamalı bir katman sistemi:

```
[1] ISSAI (164K gerçek Türkçe ses)
        ↓  LoRA → merge_and_unload()
[2] voiceflow-whisper-tr    ← Genel Türkçe base (bir kez eğitilir, nadiren güncellenir)
        ↓  + IT kayıtları (gerçek geliştirici sesi)
        ↓  LoRA → merge_and_unload()
[3] voiceflow-whisper-it    ← IT base (IT kayıtları arttıkça güncellenir)
        ↓  + Müşteri verisi
        ↓  LoRA (MERGE EDİLMEZ — müşteri makinesinde kalır)
[4] akbank_v1 / turkcell_v1 ← Müşteri delta (~30MB)
```

### Neden Merge?

- `merge_and_unload()` → LoRA ağırlıkları base modele yazılır → yeni base
- Yeni base üzerine bir sonraki katmanın LoRA'sı oturur
- Sonuç: standart HuggingFace/MLX model (inference'ta ek yük yok)

### Neden Müşteri Adapter'ı Merge Edilmez?

- Müşteri adapter'ı (~30MB) müşteri makinesinde on-premise kalır
- Veri müşteri yerinden çıkmaz → KVKK doğal uyum
- Bizim IT base'i gönderilir (~1.5GB), üzerine adapter yüklenir

### Güncelleme Stratejisi

| Katman | Ne Zaman Güncellenir |
|---|---|
| voiceflow-whisper-tr | Nadiren (ISSAI v2, büyük TR dataset eklenince) |
| voiceflow-whisper-it | IT kayıt havuzu büyüdükçe (50+ yeni kayıt) |
| Müşteri adapter | Müşteri kendi datasını genişletince |

---

## Durum

| Adapter | Durum | Versiyon |
|---|---|---|
| Qwen Adapter | ✅ Canlıda | v1 (GECTurk + corruption, 71K pair, RunPod RTX 4090) |
| voiceflow-whisper-tr | ✅ HF'te hazır | Stage 1: ISSAI 164K pair, H100 ~4.6 saat, `tkosen/voiceflow-whisper-tr` |
| voiceflow-whisper-tr-v2 | 🔄 Başlatılacak | Stage 2: noktalama/büyük harf, aynı ISSAI WAV + _clean_gt() GT |
| voiceflow-whisper-it | 🔲 Planlandı | whisper-tr-v2 merge sonrası, IT kayıtlarıyla |
| Müşteri Adapter | 🔲 Planlandı | İlk kurumsal satış sonrası |

---

## Müşteriye Özel Adapter

```
voiceflow-whisper-it (bizden)
    └── + Akbank ses verisi → akbank_v1 LoRA (~30MB, on-premise)
    └── + Turkcell ses verisi → turkcell_v1 LoRA (~30MB, on-premise)
```

Veri müşteri makinesinde kalır, adapter ~30MB → KVKK doğal uyum.
