# 006 — Quality Monitor: Self-Improving ASR Pipeline

VoiceFlow kendi kullanım verisinden öğrenir. Hiçbir veri dışarı çıkmaz.

---

## Problem

Whisper hataları ve hallüsinasyonlar statik — her güncelleme elle yapılıyor:
- `_HALLUCINATION_PHRASES` listesi hardcoded
- Dictionary girişleri kullanıcı tarafından manuel ekleniyor
- Sistematik Whisper hataları (belirli kelimeler sürekli yanlış) keşfedilemiyor

---

## Çözüm: Background Quality Monitor

Her N kayıt sonrası arka planda çalışan bir analiz görevi:

```
Her 30 kayıt sonrası:
  ├── Trailing phrase analizi   → hallucination_phrases tablosuna ekle
  ├── raw_text→text aggregation → dictionary önerileri kuyruğu
  └── Training pill feedback    → pattern analizi
```

---

## Mimari

### DB Tabloları (yeni)

```sql
-- Dinamik hallüsinasyon phrase listesi (hardcoded liste yerine)
CREATE TABLE hallucination_phrases (
    id        INTEGER PRIMARY KEY,
    phrase    TEXT UNIQUE,
    source    TEXT,  -- 'manual' | 'auto_detected'
    count     INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Dictionary önerileri kuyruğu (insan onayı bekleyen)
CREATE TABLE dict_suggestions (
    id          INTEGER PRIMARY KEY,
    user_id     TEXT,
    whisper_out TEXT,   -- Whisper'ın yanlış yazdığı
    correct     TEXT,   -- doğru form
    evidence    INTEGER DEFAULT 1,  -- kaç kez gözlemlendi
    source      TEXT,   -- 'correction' | 'feedback'
    applied     BOOLEAN DEFAULT FALSE,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### `services/quality_monitor.py`

```python
class QualityMonitor:
    ANALYSIS_INTERVAL = 30  # her 30 kayıt sonrası analiz

    async def maybe_run(self, recording_count: int) -> None:
        if recording_count % self.ANALYSIS_INTERVAL == 0:
            await self.analyze()

    async def analyze(self) -> None:
        await self._detect_hallucination_phrases()
        await self._aggregate_correction_pairs()
        await self._process_feedback_patterns()
```

### Analiz Modülleri

**1. Trailing Phrase Detector**
- Son 200 transkripsiyonun son 5 kelimesini topla
- N-gram frekans analizi
- %15+ görünme oranı → `hallucination_phrases` tablosuna ekle
- Whisper `transcribe()` bu tabloyu DB'den okur (hardcoded liste + DB birleşimi)

**2. Correction Pair Aggregator**
- `corrections` tablosundan `raw_text != NULL` kayıtları al
- Token-level diff: hangi kelime → hangi kelimeye dönüştü
- 3+ tekrar eden çift → `dict_suggestions` kuyruğuna ekle
- Kullanıcı Settings'ten onaylayabilir / reddedebilir

**3. Feedback Pattern Analyzer**
- `correction_feedback` tablosundan `user_action='edited'` kayıtları
- Training pill'den işaretlenen kelimeler → frekans analizi
- 2+ kez işaretlenen kelime → `dict_suggestions` kuyruğuna ekle

---

## Uygulama Akışı

```
RecordingService.stop() tamamlandı
    ↓
recording_count += 1
QualityMonitor.maybe_run(recording_count)
    ↓ (asyncio.create_task — non-blocking)
analyze() → DB'ye yaz
    ↓
Bir sonraki transcribe()'da:
  - hallucination_phrases: DB + hardcoded birleşimi
  - dict_suggestions: Settings'te "Öneriler" bölümünde göster
```

---

## Settings UI (Öneriler Bölümü)

```
Settings → Sözlük → Öneriler
┌────────────────────────────────────────┐
│ VoiceFlow sizin için öğrendi:          │
│                                        │
│ "tş" → "teşekkür"    [Ekle] [Yoksay]  │
│ "tamam mı" → "tamam"  [Ekle] [Yoksay]  │
│ "falan" → (sil)       [Ekle] [Yoksay]  │
└────────────────────────────────────────┘
```

---

## Ses Dosyası (İleride — Phase 2)

- Son 20 WAV → `/tmp/voiceflow_audio_cache/`
- Background: Whisper'a tekrar ver → önceki çıktıyla karşılaştır
- Drift tespiti: model cache bozulmuş mu?
- KVKK: analiz sonrası WAV otomatik silinir, sadece metin kalır

---

## Faz Planı

| Faz | İş | Süre |
|---|---|---|
| P1 | `hallucination_phrases` DB tablosu + dynamic loading | 2 saat |
| P1 | Trailing phrase detector + auto-add | 3 saat |
| P2 | Correction pair aggregator + dict_suggestions tablosu | 4 saat |
| P2 | Settings UI: Öneriler bölümü | 3 saat |
| P3 | Feedback pattern analyzer | 2 saat |
| P3 | WAV cache + drift detection | 1 gün |

---

## Neden Değerli

- **Müşteriye özgü kalite:** Şirketin jargonu otomatik öğrenilir
- **Sıfır çaba:** Kullanıcı sadece normal çalışır, sistem arka planda iyileşir
- **KVKK uyumlu:** Hiçbir ses/metin dışarıya çıkmaz, sadece istatistik
- **Satış mesajı:** "VoiceFlow her gün biraz daha sizi tanıyor"
