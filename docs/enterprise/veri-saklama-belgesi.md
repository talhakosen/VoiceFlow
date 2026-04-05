# VoiceFlow — Veri Saklama ve İşleme Belgesi

> **Sürüm:** 1.0 | **Tarih:** Nisan 2026  
> **Hedef kitle:** IT güvenlik ekipleri, KVKK/BDDK uyum sorumluları, tedarikçi onboarding süreçleri

---

## 1. Özet

VoiceFlow, kurumsal ortamlarda **tamamen yerinde (on-premise)** çalışır. Hiçbir ses kaydı, transkript metni veya kullanıcı verisi kurumun sunucu altyapısının dışına çıkmaz. Bu belge, işlenen verilerin türünü, saklandığı yeri ve korunma yöntemlerini açıklar.

---

## 2. İşlenen Veri Türleri

| Veri Türü | KVKK Sınıfı | Saklama Yeri | Yurt Dışına Çıkıyor mu? |
|---|---|---|---|
| Ses kaydı (geçici, RAM) | Biyometrik veri benzeri | Yalnızca RAM | **Hayır** |
| Transkript metni | Kişisel veri | SQLite (on-premise) | **Hayır** |
| Kullanıcı adı, departman | Kişisel veri | SQLite (on-premise) | **Hayır** |
| Kullanıcı e-posta, şifre hash | Kişisel veri | SQLite (on-premise) | **Hayır** |
| Kişisel sözlük (jargon, isimler) | Kişisel veri | SQLite (on-premise) | **Hayır** |
| Kullanım istatistikleri | Kişisel olmayan | SQLite (on-premise) | **Hayır** |
| Yapay zeka modeli ağırlıkları | Teknik veri | Sunucu diski | **Hayır** |

> **Ses kaydı hiçbir zaman diske yazılmaz.** Mikrofon → RAM buffer → Whisper modeli → RAM'den silinir. Saklanan yalnızca transkript metnidir.

---

## 3. Veri Akış Diyagramı

```
[Kullanıcı Mikrofonu]
        │
        ▼ (şifreli RAM, hiç diske gitmez)
[VoiceFlow Mac Uygulaması]
        │ HTTP (127.0.0.1 — sadece localhost)
        ▼
[VoiceFlow Backend — Şirket Sunucusu]
        │
        ├─► [Whisper Modeli — Şirket GPU/CPU]
        │         └─► Transkript metni
        │
        ├─► [Qwen LLM — Şirket GPU/CPU]  (isteğe bağlı düzeltme)
        │         └─► Düzeltilmiş metin
        │
        └─► [SQLite DB — Şirket Sunucusu]
                  └─► Transkript geçmişi, sözlük, kullanıcılar
```

**Dış ağ bağlantısı yok.** Tüm işlem şirket altyapısında gerçekleşir.

---

## 4. Veri Saklama Detayları

### 4.1 SQLite Veritabanı

| Özellik | Değer |
|---|---|
| Konum | Şirket sunucusu — `~/.voiceflow/voiceflow.db` |
| Şifreleme (beklemede) | SQLCipher AES-256, `DB_ENCRYPTION_KEY` env var ile |
| Şifreleme (iletimde) | Yalnızca localhost → şifreleme gerektirmez |
| Yedekleme | Şirketin kendi yedekleme politikasına bırakılmıştır |
| Tenant izolasyonu | Her kurum kendi `tenant_id` altında izole çalışır |

### 4.2 Saklanan Tablolar

```
transcriptions      — transkript geçmişi (metin, dil, süre, kullanıcı)
users               — kullanıcı hesapları (e-posta, bcrypt hash, rol)
user_dictionary     — kişisel/takım sözlüğü
snippets            — sesli şablonlar
audit_log           — erişim ve değişiklik kayıtları (KVKK gereği)
token_blacklist     — oturum kapatma kayıtları
```

### 4.3 Saklama Süreleri (Öneri)

| Veri | Önerilen Süre | Silme Yöntemi |
|---|---|---|
| Transkript geçmişi | 1 yıl | `DELETE /api/history` veya admin paneli |
| Kullanıcı hesabı | Çalışan ayrılışında | `DELETE /admin/users/:id/data` |
| Audit log | 3 yıl (KVKK uyum) | Manuel DB temizliği |
| JWT blacklist | Token expire süresi | Otomatik (purge_expired_tokens) |

---

## 5. Erişim Kontrolü

| Katman | Mekanizma |
|---|---|
| Ağ | Backend sadece `127.0.0.1` (local) veya iç ağ (server mode) dinler |
| API | `X-API-Key` header veya JWT Bearer token zorunlu |
| Rol bazlı | superadmin / admin / member — her rol kendi verisine erişir |
| Şifre | bcrypt (cost factor 12) — plaintext şifre hiç saklanmaz |
| Token | JWT (HS256), 60 dakika TTL, logout ile anında geçersiz kılınır |
| Audit | Her login, config değişikliği ve veri silme audit_log'a yazılır |

---

## 6. KVKK Uyum Beyanı

| KVKK Maddesi | VoiceFlow Yaklaşımı |
|---|---|
| Md. 4 — Veri işleme ilkeleri | Amaca bağlı (STT), en az veri, doğru ve güncel |
| Md. 6 — Özel nitelikli veri (ses) | On-premise → yurt dışı aktarım yok |
| Md. 7 — Silme ve imha | `DELETE /admin/users/:id/data` — kalıcı silme API |
| Md. 10 — Aydınlatma yükümlülüğü | Kurum tarafından karşılanır (VoiceFlow veri işleyen) |
| Md. 12 — Güvenlik tedbirleri | AES-256 (SQLCipher), JWT, RBAC, audit log, rate limiting |
| Md. 17 — Veri sorumlusu/işleyen | Kurum: Veri Sorumlusu; VoiceFlow: Veri İşleyen |

**VoiceFlow, KVKK kapsamında Veri İşleyendir.** Veri Sorumlusu kurumla imzalanacak **Veri İşleme Sözleşmesi (DPA)** hazırdır.

---

## 7. BDDK Uyum Beyanı

| BDDK Gereksinimi | VoiceFlow Durumu |
|---|---|
| Verinin yurt içinde kalması | ✅ Tüm veri şirket sunucusunda |
| Public cloud yasağı | ✅ On-premise only — AWS/Azure kullanılmaz |
| ISO 27001 | 🔄 Hazırlık süreci (Ekim 2026 hedef) |
| Yıllık penetrasyon testi | 📋 Planlı (2026 Q3) |
| BCP/DRP | ✅ `docs/enterprise/policies/business-continuity-plan.md` |
| Güvenli SDLC | ✅ Git-based, code review, audit log |

---

## 8. Teknik Güvenlik Kontrolleri

| Kontrol | Durum | Detay |
|---|---|---|
| Veri şifreleme (beklemede) | ✅ | SQLCipher AES-256 (ISO R-001) |
| Veri şifreleme (iletimde) | ✅ | Localhost only / kurumsal TLS |
| Rate limiting | ✅ | slowapi: 60/dk API, 10/dk auth |
| CORS | ✅ | Konfigürasyona göre kısıtlı |
| JWT token revocation | ✅ | Logout blacklist + JTI kontrolü |
| Audit log | ✅ | Append-only SQLite |
| Brute-force koruması | ✅ | Login 10/dk rate limit |
| Güvenli şifre saklama | ✅ | bcrypt cost=12 |
| Tenant izolasyonu | ✅ | Her sorgu tenant_id filtreli |

---

## 9. İletişim ve Sözleşme

**DPA (Veri İşleme Sözleşmesi):** Talep üzerine hazırlanır.  
**Teknik güvenlik soruları:** Kurumun IT güvenlik ekibiyle doğrudan teknik görüşme yapılabilir.  
**Denetim hakkı:** Kurum, VoiceFlow sistemini yerinde veya uzaktan denetleyebilir.

---

*Bu belge, kurumun KVKK/BDDK uyum süreçleri ve tedarikçi güvenlik değerlendirmeleri için hazırlanmıştır.*
