# VoiceFlow — Veriler Nerede Saklanır?

> Sürüm: 1.0 | Tarih: 2026-04-05 | Hedef kitle: IT/Güvenlik ekipleri

Bu belge, VoiceFlow'un hangi verileri topladığını, nerede sakladığını ve nasıl koruduğunu açıklar. Müşteri IT/güvenlik onay süreçlerinde ve KVKK/BDDK uyum değerlendirmelerinde kullanılmak üzere hazırlanmıştır.

---

## 1. Veri Akışı — Özet

```
Kullanıcı sesi → Mac mikrofon → VoiceFlow (RAM buffer)
                                      │
                             Whisper (on-premise)
                                      │
                            Transkript metni (RAM)
                                      │
                         LLM düzeltme (on-premise, opsiyonel)
                                      │
                           SQLite DB (şifreli, disk)
```

**Ses verisi hiçbir zaman diske yazılmaz.** İşlem RAM'de gerçekleşir, tamamlanınca silinir.

---

## 2. Veri Kategorileri ve Konumları

| Veri | Konum | Şifreleme | Süre |
|---|---|---|---|
| Ham ses kaydı (WAV buffer) | RAM (geçici) | — | Transkripsiyon sonrası silinir |
| Transkript metni | Yerel SQLite | AES-256 (SQLCipher) | Kullanıcı seçimine göre |
| Kullanıcı sözlüğü | Yerel SQLite | AES-256 (SQLCipher) | Silinene kadar |
| Sesli şablonlar (snippets) | Yerel SQLite | AES-256 (SQLCipher) | Silinene kadar |
| IT transkript kayıtları (eğitim WAV) | Yerel disk (opsiyonel) | Disk şifreleme (macOS FileVault) | Manuel silinene kadar |
| Whisper model ağırlıkları | Yerel disk | — (okuma-only) | Kalıcı |
| LLM model ağırlıkları | Yerel disk | — (okuma-only) | Kalıcı |
| Uygulama logları | `/tmp/voiceflow.log` | — | 10 MB × 5 döngüsel |
| JWT oturum token'ları | Keychain (macOS) | AES-256 (Keychain) | Token süresi kadar |

---

## 3. Dış Ağ Bağlantısı

### On-Premise (Varsayılan) Mod

**Hiçbir ses verisi, transkript veya kullanıcı verisi kurum dışına çıkmaz.**

Kurulan tek dış bağlantılar:
- Model indirme: Hugging Face (kurulum sırasında, tek seferlik). Kurumsal ortamlarda bu adım air-gap sunucudan da yapılabilir.
- VERBİS/KVKK bildirimleri: kurum yükümlülüğündedir.

### Sunucu (Server) Modu

Kurum kendi sunucusuna (şirket içi veya özel bulut) kurar. Ses verisi makul gecikmede kurum ağı üzerinden sunucuya iletilir. Sunucu dışında hiçbir servise trafik gitmez.

---

## 4. Veritabanı Güvenliği

- **Şifreleme:** SQLCipher (AES-256-CBC, cipher_page_size=4096, kdf_iter=64.000, HMAC-SHA512)
- **Anahtar yönetimi:** `DB_ENCRYPTION_KEY` ortam değişkeni; kurumsal ortamlarda HSM veya Vault entegrasyonu önerilir
- **Konum:** `~/.voiceflow/voiceflow.db` (yapılandırılabilir, `DB_PATH`)
- **Erişim:** Yalnızca çalışan VoiceFlow işlemi; dosya sistemi izinleri 600 (owner-only)

---

## 5. Kişisel Veri İşleme (KVKK)

| KVKK Maddesi | VoiceFlow Uyumu |
|---|---|
| Md. 6 — Biyometrik veri (ses) | Ses RAM'de işlenir, diske yazılmaz; on-premise → yurt dışı transfer yok |
| Md. 11 — İlgili kişi hakları | `DELETE /admin/users/:id/data` API: tüm veriler kalıcı silinir |
| Md. 12 — Veri güvenliği | SQLCipher şifreleme, log rotation, audit log, erişim kontrolü |
| Md. 16 — VERBİS kaydı | Ses verisi işlediği için kayıt zorunlu; tedarikçi olarak DPA imzalanır |

**Silme API'si:** `DELETE /admin/users/{user_id}/data` çağrısı şunları kalıcı olarak siler:
- Tüm transkript kayıtları
- Kullanıcı sözlüğü girişleri
- Sesli şablonlar
- Geri bildirim verileri (ham ses + düzeltme çiftleri)
- Kullanıcı hesabı (soft-delete)

---

## 6. BDDK Uyum Noktaları

| BDDK Gereksinimi | VoiceFlow Durumu |
|---|---|
| Birincil sistem yurt dışında barındırılamaz | On-premise; sunucu bankada fiziksel olarak bulunur |
| Tedarikçi ISO 27001 | Hedef: Ekim 2026 (bkz. `iso27001-preparation.md`) |
| Yıllık penetrasyon testi | Planlandı: Q3 2026 |
| BCP/DRP | Bkz. `policies/business-continuity-plan.md` |
| Güvenli SDLC | GitHub branch koruma, code review, CI lint/test |

---

## 7. Erişim Denetimi

- **Kimlik doğrulama:** JWT (HS256, 60 dk. access + 7 gün refresh); sunucu modunda zorunlu
- **Roller:** superadmin / admin / member — her katmanda yetki sınırı
- **Oturum sonlandırma:** `POST /auth/logout` token'ı blacklist'e ekler (JTI revocation)
- **Rate limiting:** login/register 10/dk, transkripsiyon 30/dk, genel 60/dk
- **Audit log:** login, config_change, history_clear, veri_silme; append-only SQLite tablosu

---

## 8. Veri Saklama ve İmha

| Veri | Varsayılan Süre | İmha Yöntemi |
|---|---|---|
| Transkriptler | Sınırsız (kullanıcı seçimine göre) | `DELETE /api/history` veya kişisel veri silme API'si |
| Eğitim WAV dosyaları | Manuel | Dosya sistemi silme + `shred` (güvenli imha) |
| Loglar | 50 MB döngüsel (5 × 10 MB) | Otomatik üzerine yazma |
| JWT blacklist | Token süresi kadar | `purge_expired_tokens()` periyodik temizlik |

---

## 9. Teknik Özet (IT için tek sayfa)

```
✓ Ses verisi diske yazılmaz — yalnızca RAM
✓ Transkriptler AES-256 şifreli SQLite'da saklanır (yerelde)
✓ Yurt dışına veri çıkmaz (on-premise mod)
✓ KVKK Md. 11 silme hakkı: API üzerinden tüm kişisel veriler silinebilir
✓ JWT ile oturum yönetimi + logout blacklist
✓ Audit log: tüm kritik aksiyonlar izlenir
✓ Rate limiting: kaba kuvvet saldırısı koruması
✓ Log rotation: hassas loglar birikmez
✓ ISO 27001 hazırlığı aktif (hedef: Q4 2026)
```

---

## 10. İletişim

Güvenlik soruları, DPA talebi veya denetim için: **security@voiceflow.ai**
