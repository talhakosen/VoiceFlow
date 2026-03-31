# Correction Pipeline Mimarisi — Şimdi vs Hedef

> Tarih: 31 Mart 2026
> Konu: Uçtan uca akış — kullanıcı konuşur → text oluşur

---

## Şu Anki Durum (v0.3)

```
Kullanıcı Fn'e basar
    │
    ▼
┌─────────────────┐
│  Ses Kaydı       │  macOS mikrofon → WAV buffer
│  (RecordingService)│
└────────┬────────┘
         │ Fn bırakır
         ▼
┌─────────────────┐
│  Whisper ASR     │  mlx-whisper (local) / faster-whisper (server)
│                  │  → raw transcript
└────────┬────────┘
         │ "bugun yani toplanti saat dortte hayir ucte basliyo sey hazir ol"
         ▼
┌─────────────────┐
│  LLM Correction  │  Qwen 7B + UZUN system prompt + 5 few-shot
│  (opsiyonel)     │  → 800 token prompt overhead
│                  │  → ~2-5 saniye
└────────┬────────┘
         │ "Bugün toplantı saat üçte başlıyor, hazır ol."  (bazen...)
         ▼
┌─────────────────┐
│  Snippet Match   │  "personal email" → user@example.com
│  Dictionary Fix  │  kelime bazlı replace
└────────┬────────┘
         │
         ▼
    Cmd+V → Paste
```

**Problemler:**
- LLM generic — backtracking'i bazen anlıyor bazen anlamıyor
- Filler'ları bazen siliyor bazen bırakıyor
- 800 token prompt her seferinde gönderiliyor
- Context yok — hangi uygulamada olduğunu bilmiyor (ton hariç)

---

## Hedef Durum (Fine-tuned Model + Training Mode)

```
Kullanıcı Fn'e basar
    │
    ├──────────────────────────────┐
    ▼                              ▼
┌─────────────────┐    ┌─────────────────────┐
│  Ses Kaydı       │    │  Context Capture     │  ← YENİ (PARALEL)
│  (mikrofon→WAV)  │    │  • Aktif uygulama    │
│                  │    │  • Pencere başlığı   │
│                  │    │  • Seçili metin       │
└────────┬────────┘    └──────────┬──────────┘
         │ Fn bırakır              │
         ▼                         │
┌─────────────────┐               │
│  Whisper ASR     │               │
│  mlx-whisper     │               │
└────────┬────────┘               │
         │ raw transcript          │ context
         ▼                         ▼
┌──────────────────────────────────────────┐
│          Fine-Tuned Corrector             │
│                                          │
│  Model: Qwen 7B + LoRA adapter (~20MB)   │
│  Prompt: KISA (50 token vs 800 token)    │
│                                          │
│  Input:  "bugun yani toplanti saat       │
│           dortte hayir ucte basliyo       │
│           sey hazir ol"                   │
│          + context: "Mail.app - Re: Q3"  │
│                                          │
│  Modelin ÖĞRENDİĞİ davranışlar:         │
│  ✓ Filler silme (yani, şey → kaldır)    │
│  ✓ Backtrack (dörtte hayır üçte → üçte) │
│  ✓ Turkish char (basliyo → başlıyor)    │
│  ✓ Noktalama (bağlama göre , . ? !)     │
│  ✓ Ton (Mail.app → formal)              │
│                                          │
│  Output: "Bugün toplantı saat üçte       │
│           başlıyor, hazır ol lütfen."    │
│                                          │
│  Süre: ~0.5-1s (kısa prompt sayesinde)   │
└────────────────┬─────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────┐
│          Post-Processing                  │
│                                          │
│  1. Dictionary check (fonetik eşleme)    │
│     "ant row pick" → "Anthropic"         │
│     "apvyumodel" → "AppViewModel"        │
│                                          │
│  2. Snippet match                        │
│     "kişisel email" → user@example.com   │
│                                          │
│  3. Spoken punctuation                   │
│     "virgül" → ,  "nokta" → .            │
│                                          │
│  4. Safety guard                         │
│     boş output? → raw transcript dön     │
│     çok uzun? → raw transcript dön       │
└────────────────┬─────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────┐
│          Paste + Feedback Loop            │
│                                          │
│  Cmd+V → aktif uygulamaya yapıştır       │
│                                          │
│  SQLite'a kaydet:                        │
│  { raw_whisper, model_output,            │
│    app_context, timestamp }              │
│                                          │
│  Training Mode açıksa → Pill göster:     │
│  ┌────────────────────────────────────┐  │
│  │ "Bugün toplantı saat üçte..."      │  │
│  │      [✓ Doğru]  [✗ Düzelt]        │  │
│  └────────────────────────────────────┘  │
│                                          │
│  Kullanıcı düzeltirse → feedback pair    │
│  → sonraki eğitim verisine girer         │
└──────────────────────────────────────────┘
```

---

## Farkın Özeti

| | Şimdi | Fine-tuned |
|---|---|---|
| **Prompt** | 800 token (system + 5 few-shot) | ~50 token |
| **Filler removal** | Prompt talimatı (güvenilmez) | Modele gömülü |
| **Backtracking** | Yok | Modele gömülü |
| **Turkish chars** | Few-shot ile (inconsistent) | Binlerce örnekten öğrenmiş |
| **Latency** | ~2-5s | ~0.5-1s |
| **Context** | Sadece app bundle ID → ton | Pencere başlığı + seçili metin |
| **Öğrenme** | Statik | Her kullanıcı düzeltmesi = yeni data |

---

## Teknoloji Haritası (Katman Katman)

```
KATMAN          TEKNOLOJİ              KONUM
──────          ──────────              ─────
Ses kaydı       AVAudioRecorder         Swift (Mac app)
Context         NSWorkspace + AX API    Swift (Mac app)  ← YENİ
Transport       HTTP POST /api/stop     Swift → Python
ASR             mlx-whisper             Python (MLX, local)
                faster-whisper          Python (NVIDIA, server)
Correction      Qwen 7B + LoRA         Python (MLX, local)  ← FINE-TUNED
                Qwen 7B + GGUF         Ollama (NVIDIA, server)
Dictionary      SQLite lookup           Python
Snippets        SQLite trigger match    Python
Post-process    Regex + rules           Python
Paste           NSPasteboard + Cmd+V    Swift (Mac app)
Feedback Pill   NSPanel + SwiftUI       Swift (Mac app)  ← YENİ
Storage         SQLite + aiosqlite      Python
Training        mlx_lm.lora            Python (MLX)  ← YENİ
```

---

## Yeni Bileşenler (3 tane)

### 1. Context Capture (Swift)

```swift
// Kayıt başladığında PARALEL çalışır
let appName = NSWorkspace.shared.frontmostApplication?.localizedName
let windowTitle = // AXUIElement focused window title
let selectedText = // AXUIElement selected text attribute

// Backend'e header olarak gönder
request.setValue(appName, forHTTPHeaderField: "X-Active-App")
request.setValue(windowTitle, forHTTPHeaderField: "X-Window-Title")
request.setValue(selectedText, forHTTPHeaderField: "X-Selected-Text")
```

### 2. Training Pill (Swift)

```swift
// Paste'ten sonra pill göster (Training Mode açıksa)
if trainingModeEnabled {
    showTrainingPill(
        text: correctedText,
        onApprove: { saveFeedback(.approved) },
        onEdit: { showEditField(prefilled: correctedText) },
        autoDismissAfter: 5.0  // 5sn sonra otomatik ✓
    )
}
```

### 3. Feedback → Training Pipeline (Python)

```bash
# Feedback'leri JSONL'e çevir
python -m scripts.training.harvest_feedback

# Synthetic + feedback birleştir
python -m scripts.training.prepare_dataset

# Eğit (20dk)
python -m mlx_lm.lora --train --config finetune/lora_config.yaml

# Değerlendir
python -m scripts.training.evaluate
```

---

## Eğitim Nerede Yapılır?

Mac'te (MLX LoRA). Neden:

- 7B 4-bit LoRA: Mac M2/M3 Pro'da **15-20 dakika**
- Veri makineden çıkmaz → **KVKK uyumlu**
- İterasyon hızlı: data değiştir → train → 20dk → test → tekrar
- Sıfır maliyet

RunPod'a geçiş sadece: 13B+ model veya 50K+ data durumunda.

---

## Müşteriye Özel Adapter

```
Base Adapter (VoiceFlow genel Türkçe/İngilizce)
  ├── Akbank Adapter  (+bankacılık: BIST, teminat, kredi tahsis)
  ├── Turkcell Adapter (+telekom: BTS, roaming, churn)
  └── THY Adapter     (+havacılık: NOTAM, ETD, gate)
```

Her müşteri kendi adapter'ını kendi cihazında eğitir.
Wispr Flow bunu yapamaz — cloud-only, herkes aynı model.

**Satış:** "VoiceFlow şirketinize özel öğrenir — verileriniz asla dışarı çıkmadan."
