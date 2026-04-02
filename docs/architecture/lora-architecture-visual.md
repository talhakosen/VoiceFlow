# LoRA Fine-Tuning — Mimari Görselleştirme

## 1. Uçtan Uca Pipeline

```
Kullanıcı konuşur (Fn double-tap)
           ↓
    🎙️ Mikrofon (macOS)
           ↓
    ┌─────────────────┐
    │  RecordingService│
    │  (Python backend)│
    └────────┬────────┘
             │ ham ses (float32 array)
             ↓
    ┌─────────────────┐
    │ WhisperTranscriber│
    │ mlx-whisper      │
    │ small-mlx model  │
    └────────┬────────┘
             │ raw_text
             │ "bu sabah ee saat dokuzda
             │  toplantimiz var yani"
             ↓
    ┌──────────────────────────────┐
    │        LLMCorrector          │
    │                              │
    │  system prompt               │
    │  + raw_text                  │
    │         ↓                    │
    │  ┌─────────────────────┐     │
    │  │  Qwen2.5-7B (4GB)   │     │
    │  │  ┌───────────────┐  │     │
    │  │  │ LoRA Adapter  │  │     │
    │  │  │   (39MB)      │  │     │
    │  │  └───────────────┘  │     │
    │  └─────────────────────┘     │
    │         ↓                    │
    │  corrected_text              │
    └────────┬─────────────────────┘
             │ "Bu sabah saat dokuzda
             │  toplantımız var."
             ↓
    ┌─────────────────┐
    │    SQLite DB    │◄── raw_text + corrected
    │  voiceflow.db   │    + processing_ms
    └────────┬────────┘    + user_id / tenant_id
             │
             ↓
    ┌─────────────────┐
    │  Swift App      │
    │  CGEvent Cmd+V  │
    └────────┬────────┘
             │
             ↓
    📋 Aktif pencereye yapıştır
```

---

## 2. LLMCorrector İç Akışı

```
┌──────────────────────────────────────────────────────────┐
│                      LLMCorrector                        │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │ PROMPT                                             │  │
│  │                                                    │  │
│  │  [system] Sen bir Türkçe düzeltme asistanısın...   │  │
│  │                                                    │  │
│  │  [user]   bu sabah ee saat dokuzda                 │  │
│  │           toplantimiz var yani                     │  │
│  └─────────────────────┬──────────────────────────────┘  │
│                        │ token'lara çevrilir              │
│                        ↓                                  │
│  ┌─────────────────────────────────────────────────────┐ │
│  │               Qwen2.5-7B                            │ │
│  │                                                     │ │
│  │  layer 0 ──► [Q] [K] [V]                           │ │
│  │               ↕    ↕    ↕                           │ │
│  │              [lora_a × lora_b]  ← adapter           │ │
│  │  layer 1 ──► [Q] [K] [V]                           │ │
│  │               ↕    ↕    ↕                           │ │
│  │              [lora_a × lora_b]                      │ │
│  │  ...                                                │ │
│  │  layer 27 ──► [Q] [K] [V]                          │ │
│  │               ↕    ↕    ↕                           │ │
│  │              [lora_a × lora_b]                      │ │
│  │                      ↓                              │ │
│  │           token olasılıkları hesapla                │ │
│  │                      ↓                              │ │
│  │    "Bu" → "sabah" → "saat" → "dokuzda" → ...       │ │
│  └─────────────────────┬───────────────────────────────┘ │
│                        │ token'lar → metne çevrilir       │
│                        ↓                                  │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ OUTPUT                                              │ │
│  │                                                     │ │
│  │  [assistant]  Bu sabah saat dokuzda                 │ │
│  │               toplantımız var.                      │ │
│  │                                                     │ │
│  │  "ee" → silindi    (filler removal)                 │ │
│  │  "yani" → silindi  (filler removal)                 │ │
│  │  "toplantimiz" → "toplantımız"  (Türkçe karakter)   │ │
│  │  "bu sabah" → "Bu sabah"        (büyük harf)        │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

---

## 3. Tek Layer — Attention Detayı

```
INPUT TOKEN: "toplantimiz"
      │
      ▼
   [●●●●●●●]  embedding [512 boyut]
      │
      ╔═══════════════════════════════════════╗
      ║           LAYER N / 28               ║
      ║                                       ║
      ║   ┌─────────────────────────────┐    ║
      ║   │      SELF-ATTENTION         │    ║
      ║   │                             │    ║
      ║   │         [512] giriş         │    ║
      ║   │           /    |    \       │    ║
      ║   │          ↓     ↓     ↓      │    ║
      ║   │   ┌──────────┐ ┌─────────┐ ┌──────────┐  │
      ║   │   │    Q     │ │    K    │ │    V     │  │
      ║   │   │ "neyi    │ │"nelerle │ │"ne       │  │
      ║   │   │  arıyorum│ │ eşleş"  │ │ alacağım │  │
      ║   │   │    ?"    │ │         │ │    ?"    │  │
      ║   │   └────┬─────┘ └────┬────┘ └────┬─────┘  │
      ║   │        │  LoRA ↕    │  LoRA ↕   │  LoRA ↕ │
      ║   │   ┌────▼─────────────▼────┐     │        │
      ║   │   │   Q × Kᵀ → skor      │     │        │
      ║   │   │  "toplantimiz" ne     │     │        │
      ║   │   │  kadar "toplantımız"  │     │        │
      ║   │   │  ile ilişkili?        │     │        │
      ║   │   │        ↓              │     │        │
      ║   │   │   softmax(skor)       │     │        │
      ║   │   └────────────┬──────────┘     │        │
      ║   │                └────── × ───────┘        │
      ║   │                         ↓                │
      ║   │              context-aware [512]         │
      ║   └─────────────────────────┬───────────────┘    ║
      ║                             │                     ║
      ║   ┌─────────────────────────▼───────────────┐    ║
      ║   │                  FFN                    │    ║
      ║   │      [512] → [18944] → [512]            │    ║
      ║   │      (genişlet → sıkıştır)              │    ║
      ║   │       LoRA ↕ (gate/up/down proj)        │    ║
      ║   └─────────────────────────┬───────────────┘    ║
      ╚═══════════════════════════════════════════════════╝
      │
      · × 28 layer
      │
      ▼
  olasılık dağılımı:
  "toplantımız" → %94  ◄── doğru
  "toplantimiz" → %4
  ...
      │
      ▼
   OUTPUT: "toplantımız"
```

---

## 4. Sinir Ağı Olarak LoRA

```
INPUT TOKEN: "toplantimiz"
      │
      ▼
   [●●●●●●●]  embedding [512 boyut]
      │
      ╔═══════════════════════════════════════╗
      ║           LAYER 1 / 28               ║
      ║                                       ║
      ║   ┌─────────────────────────────┐    ║
      ║   │      ATTENTION HEADS        │    ║
      ║   │                             │    ║
      ║   │  ●─────────────────────●   │    ║
      ║   │  ●──────────────────●  ●   │    ║
      ║   │  ●───────────────●  ●  ●   │    ║
      ║   │  ●────────────●  ●  ●  ●   │    ║
      ║   │  ●─────────●  ●  ●  ●  ●   │    ║
      ║   │  ●──────●  ●  ●  ●  ●  ●   │    ║
      ║   │  ●───●  ●  ●  ●  ●  ●  ●   │    ║
      ║   │  ●  ●  ●  ●  ●  ●  ●  ●   │    ║
      ║   │   Q    K    V              │    ║
      ║   │   │    │    │              │    ║
      ║   │   ▼    ▼    ▼              │    ║
      ║   │  [●●] [●●] [●●]  BASE     │    ║
      ║   │   +    +    +              │    ║
      ║   │  [●●] [●●] [●●]  LORA ←──── eğittiğimiz
      ║   └────────────┬────────────────┘    ║
      ║                │                     ║
      ║   ┌────────────▼────────────────┐    ║
      ║   │           FFN               │    ║
      ║   │                             │    ║
      ║   │  ● ● ● ● ●     [512]       │    ║
      ║   │   \ \ | / /                 │    ║
      ║   │  ●●●●●●●●●●●   [18944]     │    ║
      ║   │   / / | \ \    BASE        │    ║
      ║   │  ● ● ● ● ●  +  LORA ←──── eğittiğimiz
      ║   │             [512]           │    ║
      ║   └────────────┬────────────────┘    ║
      ╚═══════════════════════════════════════╝
      │
      · × 28 layer
      │
      ▼
   OUTPUT: "toplantımız"
```

---

## 5. LoRA Matematiği — Neden 39MB Yeterli?

```
BASE ağırlıklar [3584 × 3584]   ← değişmez, ~4GB
       +
lora_a [3584 × 8]               ← 8 boyutlu dar geçit
    ×
lora_b [8 × 3584]               ← tekrar genişlet
       ║
       ▼
  delta W = lora_b × lora_a     ← base ile aynı boyut
                                    ama sadece 8 boyut
                                    üzerinden geçiyor

  Parametre karşılaştırma:
  BASE  Q_proj: 3584 × 3584 = 12.8M parametre
  LoRA  Q_proj: (3584×8) + (8×3584) = 57K parametre
                                       → 224x daha küçük
```
