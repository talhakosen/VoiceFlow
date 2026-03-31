# Training Mode — Kullanıcıdan Correction Feedback Toplama

> Tarih: 31 Mart 2026
> Konu: "Seni tanısın" modu — ilk 1 ay correction pill ile veri toplama

---

## Konsept

Kullanıcı Settings'ten "Training Mode"u açar. Her dikte sonrası küçük bir
onay pill'i çıkar. Kullanıcı doğrular veya düzeltir. Bu veriler modeli
eğitmek için kullanılır.

**Satış argümanı:** "İlk 1 ay bu modu açık bırakın, VoiceFlow sizi tanısın."

---

## Pill UX

### Normal Akış

```
Kullanıcı konuşur → Whisper → LLM düzeltir → Paste yapılır

Training Mode açıksa → Pill çıkar:

┌────────────────────────────────────────────┐
│  "Bugün toplantı saat üçte başlıyor."      │
│                                            │
│           [✓ Doğru]    [✗ Düzelt]          │
└────────────────────────────────────────────┘
            │                    │
            ▼                    ▼
       5sn sonra            Edit ekranı açılır
       otomatik kapanır
       (= ✓ sayılır)

```

### Düzeltme Akışı

```
Kullanıcı [✗ Düzelt]'e tıklarsa:

┌────────────────────────────────────────────┐
│  ✏️  Doğru halini yaz:                     │
│                                            │
│  [Bugün toplantı saat üçte başlıyor.     ] │  ← editable, pre-filled
│                                            │
│                    [Kaydet]                 │
└────────────────────────────────────────────┘

Kaydet → pair SQLite'a yazılır → pill kapanır
```

### Pill Davranışları

| Aksiyon | Sonuç | Eğitim değeri |
|---------|-------|---------------|
| ✓ Doğru tıkla | `approved` kaydedilir | Pozitif örnek |
| 5sn bekle (pill kapanır) | `approved` kaydedilir | Pozitif örnek |
| ✗ Düzelt → yeni text yaz | `edited` kaydedilir | **En değerli** |
| ESC / pill'i kaydır | `dismissed` kaydedilir | Atlanır |

---

## Veri Modeli

```sql
CREATE TABLE correction_feedback (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id   TEXT NOT NULL,
    user_id     TEXT,
    raw_whisper TEXT NOT NULL,        -- Whisper ham çıktısı
    model_output TEXT NOT NULL,       -- LLM'in düzeltmesi (paste edilen)
    user_action TEXT NOT NULL,        -- 'approved' | 'edited' | 'dismissed'
    user_edit   TEXT,                 -- sadece 'edited' ise dolu
    app_context TEXT,                 -- bundle ID (com.apple.Mail, ...)
    window_title TEXT,               -- pencere başlığı
    mode        TEXT,                 -- general/engineering/office
    language    TEXT,                 -- tr/en
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### API Endpoint

```
POST /api/feedback
{
    "raw_whisper": "bugun yani toplanti saat ucte basliyo",
    "model_output": "Bugün toplantı saat üçte başlıyor.",
    "user_action": "edited",
    "user_edit": "Bugün toplantı saat üçte başlıyor!",
    "app_context": "com.apple.Mail"
}
```

---

## Settings Ekranı

```
Settings → Recording → [Training Mode]

┌─────────────────────────────────────────────────┐
│  CORRECTION LEARNING                            │
│                                                 │
│  Açık ●                                         │
│  Dikte sonrası onay pill'i göster               │
│                                                 │
│  ──────────────────────────────────────         │
│  PROGRESS                                       │
│                                                 │
│  ████████████░░░░  312 / 500                    │
│  Hedef: 500 onay (önerilen ilk eğitim için)     │
│                                                 │
│  ✓ Onaylanan:   241                             │
│  ✎ Düzeltilen:   71  ← En değerliler bunlar     │
│  — Atlanan:      0                              │
│                                                 │
│  ──────────────────────────────────────         │
│  EĞİTİM                                         │
│                                                 │
│  Son eğitim: Hiç yapılmadı                      │
│                                                 │
│  [Eğitimi Başlat]  ← 500'e ulaşınca aktif       │
│                                                 │
│  ──────────────────────────────────────         │
│  [Tüm verileri sil]                             │
└─────────────────────────────────────────────────┘
```

---

## "Eğitimi Başlat" Akışı

```
[Eğitimi Başlat] butonuna basılır
    │
    ▼
1. correction_feedback'ten pair'leri çek
   - approved → (raw_whisper, model_output) pair
   - edited   → (raw_whisper, user_edit) pair  ← daha değerli
   - dismissed → atla
    │
    ▼
2. JSONL formatına çevir
   + mevcut synthetic data ile karıştır
    │
    ▼
3. mlx_lm.lora --train başlat
   ┌────────────────────────────────┐
   │  🔄 Model eğitiliyor...        │
   │  ████████░░░░░░  800/1000 iter │
   │  Kalan süre: ~4 dakika         │
   └────────────────────────────────┘
    │
    ▼
4. Tamamlandı
   ┌────────────────────────────────┐
   │  ✅ Modeliniz güncellendi!      │
   │  Önceki: WER 12% → Yeni: WER 7%│
   └────────────────────────────────┘
```

---

## Neden Pill? (Alternatifler Neden Çalışmaz)

### Problem: Paste Sonrası Düzeltmeyi Otomatik Yakalamak

| Yaklaşım | Çalışır | Çalışmaz | Neden |
|-----------|---------|----------|-------|
| AX API text monitoring | Mail, Notes, Slack | Terminal, VS Code, Electron | Standart text field değil |
| Clipboard monitoring | Copy yapan kullanıcılar | Çoğu zaman | Kullanıcı her zaman kopyalamaz |
| Terminal satır izleme | Basit komutlar | Çok satırlı input | Karmaşık, güvenilmez |
| **Explicit pill** | **Her uygulama** | — | **Kullanıcı kontrolünde** |

Pill yaklaşımı:
- Terminal, VS Code, her yerde çalışır
- Kullanıcı ne gönderildiğini görür → KVKK uyumlu
- Low friction: 5sn bekle = otomatik onay
- En değerli veri = kullanıcının aktif düzeltmesi

---

## İlk Ay Etkisi

```
Hafta 1:  ~35 correction/gün × 5 gün = 175 pair
Hafta 2:  ~35/gün = 350 toplam
Hafta 3:  ~35/gün = 525 toplam  ← İlk eğitim tetiklenebilir!
Hafta 4:  ~35/gün = 700 toplam  ← Model güncelleme

Ay 1 sonu: ~700 production pair + 4,500 synthetic = 5,200 total
           Fine-tuned model, kullanıcıya özelleşmiş
```

Kıyaslama: Günde 10 dikte × 5 dakika arası = normal iş temposu.

---

## Teknik Implementasyon Özeti

### Swift Tarafı
- `TrainingPillView`: NSPanel, paste sonrası göster, ✓/✗ buton
- `TrainingPillController`: timer (5sn auto-dismiss), edit mode
- `FeedbackService`: `POST /api/feedback` çağrısı
- Settings: toggle, progress bar, eğitim butonu

### Python Tarafı
- `correction_feedback` SQLite tablosu
- `POST /api/feedback` endpoint
- `scripts/training/harvest_feedback.py` → JSONL'e çevir
- `scripts/training/prepare_dataset.py` → synthetic + feedback birleştir

### Güvenlik
- Veriler sadece local SQLite'ta
- `[Tüm verileri sil]` butonu → KVKK gereği
- Tenant izolasyonu (çok kullanıcılı sunucuda)
