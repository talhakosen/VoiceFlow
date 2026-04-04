# Risk Kaydı

**Belge No:** VF-RSK-001  
**Versiyon:** 1.0  
**Tarih:** 2026-04-04  
**Gözden Geçirme:** 6 ayda bir

**Risk Skoru:** Olasılık (1–5) × Etki (1–5) = Toplam (1–25)  
**Kabul eşiği:** ≤ 6 | **İşlem gerekli:** 7–14 | **Acil:** ≥ 15

---

## Risk Tablosu

| ID | Risk | Tehdit | Olasılık | Etki | Skor | Kontrol | Kalan Risk |
|---|---|---|---|---|---|---|---|
| R-001 | Ses veritabanı şifresiz diskte | Fiziksel erişim / disk çalınması | 2 | 5 | **10** | SQLCipher uygula | 2 |
| R-002 | API anahtarı sızıntısı (.env) | Yanlış dosya izni / git commit | 3 | 5 | **15** | 600 izni ✅, gitignore, rotation | 4 |
| R-003 | JWT secret tahmin edilebilir | Zayıf secret kullanımı | 2 | 5 | **10** | JWT_SECRET env var, min 32 byte | 2 |
| R-004 | Yetkisiz API erişimi | Brute force / token çalınması | 2 | 4 | **8** | Rate limiting ekle, token revocation | 3 |
| R-005 | Tenant veri karışması | Kod hatası, query bug | 1 | 5 | **5** | Tenant filtering query, test | 3 |
| R-006 | Eğitim verisi sızıntısı (RunPod) | RunPod pod güvensiz bırakılması | 2 | 3 | **6** | Pod kapatma prosedürü, API key rotation | 3 |
| R-007 | Müşteri ses kaydı veri ihlali | Yetkisiz erişim / bug | 1 | 5 | **5** | Tenant izolasyonu, audit log | 3 |
| R-008 | Backend çökmesi / servis kesintisi | Kod hatası, model OOM | 3 | 3 | **9** | Force-stop mekanizması, auto-restart | 4 |
| R-009 | ML modeli manipülasyonu | Supply chain attack (HF) | 1 | 4 | **4** | Model hash doğrulama | 2 |
| R-010 | Geliştirici Mac fiziksel kaybı | Hırsızlık / kayıp | 1 | 5 | **5** | FileVault şifreleme, Time Machine | 2 |
| R-011 | KVKK bildirimi gecikmesi | İhlal tespitinde gecikme | 2 | 4 | **8** | Incident response plan, audit log | 4 |
| R-012 | Üçüncü taraf servis kesintisi (RunPod) | Bulut sağlayıcı sorunu | 2 | 2 | **4** | On-premise alternatif mevcut | 2 |

---

## Aksiyon Planı (Yüksek Riskler)

| Risk | Aksiyon | Sorumlu | Hedef Tarih |
|---|---|---|---|
| R-002 | API key rotation + .env 600 izni | Geliştirici | ✅ 2026-04-04 |
| R-001 | SQLCipher entegrasyonu | Geliştirici | 2026-04-30 |
| R-003 | JWT secret min 32 byte kontrolü | Geliştirici | 2026-04-15 |
| R-004 | Rate limiting (slowapi) | Geliştirici | 2026-04-30 |
| R-008 | Log rotation konfigürasyonu | Geliştirici | 2026-04-20 |
| R-011 | KVKK bildirim prosedürü belgele | Geliştirici | 2026-04-20 |

---

## Risk İşleme Stratejileri

- **Azalt:** Kontrol uygulayarak riski kabul edilebilir seviyeye düşür (çoğu risk)
- **Kabul:** Risk skoru ≤ 6 ve maliyet > fayda ise kabul et
- **Transfer:** Sigorta veya üçüncü taraf (gelecekte)
- **Kaçın:** Riski doğuran aktiviteden kaçın (örn: geliştirici Mac'te müşteri verisi tutmama)
