---
title: İş Sürekliliği ve Felaket Kurtarma Planı
version: 1.0
date: 2026-04-05
owner: Sistem Yönetimi
standard: ISO 27001:2022 / A.5.29, A.5.30
rto: 4 saat
rpo: 24 saat
---

# İş Sürekliliği ve Felaket Kurtarma Planı

## 1. Amaç ve Kapsam

Bu plan, VoiceFlow on-premise dağıtımında yaşanabilecek kesintilerde hizmetin belirlenen sürelerde yeniden devreye alınmasını sağlar.

**Hedefler:**
- RTO (Kurtarma Süresi Hedefi): **4 saat**
- RPO (Kurtarma Noktası Hedefi): **24 saat** (son yedekten veri kaybı)

## 2. Kritik Sistem Bileşenleri

| Bileşen | Öncelik | Açıklama |
|---|---|---|
| Backend sunucu (FastAPI) | P1 | Konuşma transkripsiyon servisi |
| SQLite veritabanı (`voiceflow.db`) | P1 | Transkript geçmişi ve kullanıcı verileri |
| Whisper modeli | P1 | Ses-metin dönüşümü |
| Qwen LLM adaptörü | P2 | Metin düzeltme (opsiyonel) |
| macOS Swift istemcisi | P2 | Kullanıcı arayüzü |
| ChromaDB (RAG) | P3 | Bilgi bankası — servis dışı kalması kritik değil |

## 3. Olay Türleri ve Kurtarma Prosedürleri

### 3.1 Backend Sunucu Arızası

**Belirtiler:** API yanıt vermiyor, `/health` endpoint erişilemiyor, kayıt başlatılamıyor.

**Kurtarma adımları:**
1. Log inceleme: `tail -100 /tmp/voiceflow.log`
2. Süreç kontrolü: `./voiceflow.sh status`
3. Yeniden başlatma: `./voiceflow.sh restart`
4. Port çakışması varsa: `lsof -ti TCP:8000 -sTCP:LISTEN | xargs kill` ardından `./voiceflow.sh start`
5. Sorun devam ederse Python venv kontrolü: `cd backend && source .venv/bin/activate && python -m uvicorn api.main:app`
6. Hata raporlama ve eskalasyon

**Tahmini süre:** 15–30 dakika

---

### 3.2 Veritabanı Bozulması veya Kaybı

**Belirtiler:** Geçmiş transkriptlere erişilemiyor, `aiosqlite` hataları loglarda.

**Kurtarma adımları:**
1. Mevcut DB durumu: `sqlite3 voiceflow.db "PRAGMA integrity_check;"`
2. Bozuk DB'yi yedek alın: `cp voiceflow.db voiceflow.db.corrupt.$(date +%Y%m%d)`
3. Son yedeği geri yükle: `cp backups/voiceflow.db.$(date +%Y%m%d) voiceflow.db`
4. Yedek yoksa boş DB ile yeniden başlat — veri kaybı kabul RPO sınırları dahilinde
5. Backend yeniden başlatma
6. Veri kaybı loglanır ve yönetim bilgilendirilir

**Yedekleme:** Günlük otomatik yedek (`voiceflow.db` → `backups/YYYY-MM-DD/`), 30 gün saklanır.

**Tahmini süre:** 30–60 dakika

---

### 3.3 AI Model Yükleme Hatası (Whisper / Qwen)

**Belirtiler:** `model_loaded: false` veya `llm_loaded: false` `/health` yanıtında, transkripsiyon başlamıyor.

**Kurtarma adımları:**
1. Model dosyaları kontrolü: `ls -la ml/whisper/models/` ve `ls -la ml/qwen/adapters_mlx/`
2. Disk alanı kontrolü: `df -h` — MLX modelleri için min 10 GB gerekli
3. `config.yaml` model yollarını doğrula
4. Backend yeniden başlat — model lazy-load yeniden denenecek
5. Whisper modeli hasarlıysa: HF'den yeniden indir (`HF_TOKEN` gerekli)
6. Qwen adaptörü hasarlıysa: `ml/qwen/adapters_mlx/` klasöründen yedek kopyayı geri yükle

**Tahmini süre:** 30 dakika – 2 saat (model indirme gerekirse)

---

### 3.4 macOS Swift Uygulaması Sorunu

**Belirtiler:** Uygulama açılmıyor, menu bar ikonı görünmüyor, erişilebilirlik izni hatası.

**Kurtarma adımları:**
1. Uygulamayı yeniden başlat: `pkill -f "VoiceFlow.app"; open /Applications/VoiceFlow.app`
2. Erişilebilirlik izni: Sistem Ayarları → Gizlilik ve Güvenlik → Erişilebilirlik → VoiceFlow'u etkinleştir
3. DerivedData temizleme ve yeniden derleme (IT gerektirir):
   ```
   rm -rf ~/Library/Developer/Xcode/DerivedData/VoiceFlowApp-*
   xcodebuild -project VoiceFlowApp/VoiceFlowApp.xcodeproj -scheme VoiceFlowApp clean build
   ```
4. Backend ayrıca çalışıyorsa manuel API erişimi mümkün (curl ile test)

**Tahmini süre:** 15–45 dakika

---

### 3.5 Sunucu Donanım Arızası (Tam Sistem Kaybı)

**Kurtarma adımları:**
1. Yedek sunucuya işletim sistemi kur
2. VoiceFlow repo'yu klon: `git clone <repo_url>`
3. Python venv oluştur: `cd backend && python3 -m venv .venv && pip install -e ".[dev,context]"`
4. Model dosyalarını yedekten geri yükle (Whisper + Qwen)
5. `config.yaml` ve `.env` dosyalarını güvenli yedekten geri yükle
6. Veritabanı yedeğini geri yükle
7. Servisi başlat ve doğrula: `./voiceflow.sh start && curl http://localhost:8000/health`

**Tahmini süre:** 2–4 saat

## 4. Yedekleme Stratejisi

| Varlık | Yöntem | Sıklık | Saklama |
|---|---|---|---|
| `voiceflow.db` | Dosya kopyası (şifreli) | Günlük | 30 gün |
| `config.yaml` | Git repo + güvenli yedek | Her değişimde | Süresiz |
| Model dosyaları | Yedek sunucu + HF | Tek seferlik kurulum | Süresiz |
| Uygulama kodu | Git repo | Her commit | Süresiz |
| ChromaDB | `~/.voiceflow/chroma/` kopyası | Haftalık | 4 hafta |

## 5. İletişim ve Eskalasyon

| Seviye | Süre | Eylem |
|---|---|---|
| L1 | 0–30 dk | IT/sistem yöneticisi sorun gideriyor |
| L2 | 30–120 dk | Kıdemli IT devreye giriyor |
| L3 | 2+ saat | VoiceFlow teknik destek hattı aranır, yönetim bilgilendirilir |

**Kritik kesinti:** RTO süresinin aşılması durumunda kurum BDDK operasyonel risk bildirimi yapıp yapmayacağına karar verir.

## 6. Test ve Tatbikat

- Yedekleme geri yükleme testi: 3 ayda bir
- BCP tatbikatı: Yılda bir (tam senaryo simülasyonu)
- Test sonuçları belgelenir ve bu plana eklenir

**Onay:** Sistem Yöneticisi / CISO — 2026-04-05
