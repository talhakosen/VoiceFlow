# VoiceFlow — ISO 27001 Hazırlık Planı

**Hedef:** ISO 27001:2022 sertifikasyonu  
**Tahmini süre:** 6–8 ay  
**Belgelendirme kurumu:** TÜRKAK onaylı (BSI, TÜV SÜD, Bureau Veritas)

---

## Hazırlık Durumu (Genel)

| Faz | Konu | Durum |
|---|---|---|
| Faz 1 | Kritik teknik düzeltmeler | 🔴 Başlanıyor |
| Faz 2 | BGYS politika dokümanları | 🔴 Başlanıyor |
| Faz 3 | Varlık envanteri + risk kaydı | 🔴 Başlanıyor |
| Faz 4 | Kontrol kanıtları | ⬜ Bekliyor |
| Faz 5 | İç tetkik | ⬜ Bekliyor |
| Faz 6 | Dış denetim + sertifika | ⬜ Bekliyor |

---

## Faz 1 — Kritik Teknik Düzeltmeler

### 1.1 Data at Rest Encryption (SQLCipher)
- [ ] `backend/` → `sqlcipher3` veya `pysqlcipher3` kur
- [ ] `db/storage.py` → `aiosqlite` yerine SQLCipher bağlantısı
- [ ] `config.yaml` → `db_encryption_key` config ekle (env var'dan)
- [ ] Mevcut `voiceflow.db` migration scripti yaz
- **Kontrol:** ISO 27001 A.8.24 — Kriptografi kullanımı

### 1.2 Secrets Yönetimi
- [x] `.env` dosya izni 600 (owner-only) — **TAMAMLANDI**
- [ ] `.env.example` güncelle — tüm zorunlu değişkenler belgelensin
- [ ] Key rotation policy belirle (API key'ler 90 günde bir)
- [ ] `OPENAI_API_KEY`, `TRELLO_API_KEY` vb. rotation takvimi koy
- **Kontrol:** ISO 27001 A.8.24, A.5.17

### 1.3 API Güvenliği
- [ ] Rate limiting ekle (FastAPI `slowapi` veya nginx)
- [ ] Request/response audit log (user_id + endpoint + timestamp)
- [ ] JWT token revocation (logout → blacklist)
- [ ] Production'da X-Api-Key fallback'i kapat
- **Kontrol:** ISO 27001 A.8.20, A.8.15

### 1.4 Log Yönetimi
- [ ] Log rotation konfigürasyonu (`logging.handlers.RotatingFileHandler`)
- [ ] Log dosyası izinleri (sadece uygulama kullanıcısı okuyabilir)
- [ ] Audit log'u ayrı dosyaya yaz (transcription log'undan bağımsız)
- **Kontrol:** ISO 27001 A.8.15 — Loglama

---

## Faz 2 — BGYS Politika Dokümanları

Dosya konumu: `docs/enterprise/policies/`

| Politika | Dosya | Durum |
|---|---|---|
| Bilgi Güvenliği Politikası (ISP) | `information-security-policy.md` | 🔴 Oluşturuldu |
| Erişim Kontrol Politikası | `access-control-policy.md` | 🔴 Oluşturuldu |
| Şifreleme Politikası | `encryption-policy.md` | 🔴 Oluşturuldu |
| Olay Yönetimi Prosedürü | `incident-response-plan.md` | 🔴 Oluşturuldu |
| Veri Sınıflandırma Politikası | `data-classification-policy.md` | ⬜ Bekliyor |
| İş Sürekliliği Planı (BCP) | `business-continuity-plan.md` | ⬜ Bekliyor |
| Tedarikçi Güvenlik Politikası | `vendor-security-policy.md` | ⬜ Bekliyor |

---

## Faz 3 — Varlık Envanteri & Risk Kaydı

| Doküman | Dosya | Durum |
|---|---|---|
| Varlık Envanteri | `asset-inventory.md` | 🔴 Oluşturuldu |
| Risk Kaydı | `risk-register.md` | 🔴 Oluşturuldu |
| Kontrol Matrisi (SoA) | `statement-of-applicability.md` | ⬜ Bekliyor |

---

## Faz 4 — Kontrol Kanıtları (Denetçiye Gösterilecek)

- [ ] Penetrasyon testi raporu (bağımsız firma)
- [ ] Çalışan güvenlik farkındalık eğitimi belgesi
- [ ] Yönetim Gözden Geçirme (YGG) toplantı tutanağı
- [ ] İç tetkik raporu
- [ ] Düzeltici faaliyet kayıtları (nonconformity log)

---

## ISO 27001 Kontrol Durumu (Annex A)

| Kontrol | Açıklama | Durum | Notlar |
|---|---|---|---|
| A.5.1 | Bilgi güvenliği politikaları | 🟡 Kısmi | Politika dokümanı hazırlandı |
| A.5.15 | Erişim kontrolü | ✅ | JWT + rol tabanlı impl. |
| A.5.17 | Kimlik doğrulama | ✅ | bcrypt, JWT |
| A.6.3 | Farkındalık eğitimi | 🔴 Yok | Belge hazırlanacak |
| A.7.10 | Depolama ortamı | 🔴 Yok | SQLCipher TODO |
| A.8.4 | Kaynak koda erişim | ✅ | Private repo |
| A.8.5 | Güvenli kimlik doğrulama | ✅ | JWT impl. |
| A.8.7 | Kötü amaçlı yazılım | 🔴 Yok | Endpoint protection policy |
| A.8.12 | Veri sızıntısı önleme | 🟡 Kısmi | Tenant izolasyonu var |
| A.8.15 | Loglama | 🟡 Kısmi | Console log var, rotation yok |
| A.8.20 | Ağ güvenliği | 🔴 Yok | Network diagram + firewall rules |
| A.8.24 | Kriptografi | 🔴 Yok | SQLCipher TODO |
| A.8.28 | Güvenli kodlama | 🟡 Kısmi | Architecture var, SAST yok |

---

## Takvim

| Dönem | Hedef |
|---|---|
| Nisan 2026 | Faz 1 teknik + Faz 2/3 dokümanlar |
| Mayıs 2026 | Kontrol kanıtları topla |
| Haziran 2026 | İç tetkik |
| Temmuz 2026 | Danışman GAP analizi |
| Eylül 2026 | Dış denetim (Aşama 1) |
| Ekim 2026 | Dış denetim (Aşama 2) → Sertifika |
