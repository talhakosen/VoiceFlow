# Statement of Applicability (SoA) — ISO 27001:2022

**Kuruluş:** VoiceFlow | **Tarih:** 2026-04-05 | **Sürüm:** 1.0
**BGYS Kapsamı:** VoiceFlow macOS uygulaması, backend hizmetleri ve müşteri on-premise dağıtımları

Açıklamalar: ✓ = Uygulandı | ⬜ = Planlandı | ✗ = Kapsam dışı | — = Geçerli değil

---

## Bölüm 5 — Bilgi Güvenliği Politikaları

| Kontrol | Durum | Uygulama |
|---|---|---|
| 5.1 Bilgi güvenliği politikaları | ✓ | `information-security-policy.md` |
| 5.2 Bilgi güvenliği rolleri ve sorumlulukları | ✓ | ISP + erişim kontrol politikası |
| 5.3 Görevler ayrılığı | ✓ | rol sistemi: member/admin/superadmin |

## Bölüm 6 — İnsan Kaynakları Güvenliği

| Kontrol | Durum | Uygulama |
|---|---|---|
| 6.1 İşe alım öncesi güvenlik | ⬜ | Planlı: referans kontrolü prosedürü |
| 6.2 İstihdam koşulları | ✓ | NDA + gizlilik maddesi iş sözleşmesinde |
| 6.3 Farkındalık, eğitim | ⬜ | Planlı: yıllık güvenlik farkındalık eğitimi |
| 6.4 Disiplin süreci | ✓ | İK politikasında tanımlı |
| 6.5 İşten ayrılma | ✓ | Erişim iptali prosedürü mevcut |

## Bölüm 7 — Varlık Yönetimi

| Kontrol | Durum | Uygulama |
|---|---|---|
| 7.1 Varlıkların envanteri | ✓ | `asset-inventory.md` |
| 7.2 Varlık sahipliği | ✓ | Her varlığa sahip atanmış |
| 7.3 Kabul edilebilir kullanım | ✓ | ISP'de tanımlı |
| 7.4 Varlıkların iadesi | ✓ | İşten ayrılma prosedüründe |
| 7.5 Bilgi sınıflandırma | ✓ | `data-classification-policy.md` |
| 7.6 Etiketleme | ✓ | 4 sınıf etiketi tanımlı |
| 7.7 Taşınabilir ortam | ✓ | Şifreli yedek politikası |
| 7.8 Fiziksel ortam imhası | ✓ | `shred` + imha tutanağı |

## Bölüm 8 — Erişim Kontrolü

| Kontrol | Durum | Uygulama |
|---|---|---|
| 8.1 Erişim kontrolü politikası | ✓ | `access-control-policy.md` |
| 8.2 Ayrıcalıklı erişim | ✓ | superadmin rol; en az yetki prensibi |
| 8.3 Bilgiye erişim kısıtlama | ✓ | tenant_id izolasyonu; JWT rol kontrolü |
| 8.4 Kaynak koda erişim | ✓ | GitHub branch koruma; PR onayı zorunlu |
| 8.5 Kimlik doğrulama | ✓ | JWT HS256; bcrypt parola hash |
| 8.6 Gizli kimlik doğrulama | ✓ | `.env` dosyası 600 izin; Keychain macOS |
| 8.7 Oturum yönetimi | ✓ | Token revocation (JTI blacklist); 60dk TTL |

## Bölüm 9 — Kriptografi

| Kontrol | Durum | Uygulama |
|---|---|---|
| 9.1 Kriptografi politikası | ✓ | `encryption-policy.md` |
| 9.2 Anahtar yönetimi | ⬜ | Planlı: HSM/Vault entegrasyonu (Q3 2026) |

## Bölüm 10 — Fiziksel Güvenlik

| Kontrol | Durum | Uygulama |
|---|---|---|
| 10.1 Fiziksel güvenlik çevresi | — | On-premise: müşteri sorumluluğunda |
| 10.2 Fiziksel giriş kontrolleri | — | Müşteri sorumluluğunda |
| 10.3 Ofis güvenliği | ✓ | Uzaktan çalışma + VPN politikası |
| 10.11 Cihaz imhası | ✓ | Disk wipe prosedürü mevcut |

## Bölüm 11 — Operasyonel Güvenlik

| Kontrol | Durum | Uygulama |
|---|---|---|
| 11.1 Dokümante işletim prosedürleri | ✓ | `voiceflow.sh`; kurulum dökümantasyonu |
| 11.2 Değişim yönetimi | ✓ | GitHub PR + code review + CI |
| 11.3 Kapasite yönetimi | ✓ | Log rotation; DB boyut izleme |
| 11.4 Geliştirme/test/üretim ayrımı | ✓ | Ayrı config; local/server mod |
| 11.5 Zararlı yazılımdan koruma | ✓ | pip-audit; npm audit; bağımlılık tarama |
| 11.6 Yedekleme | ✓ | `business-continuity-plan.md`; günlük yedek |
| 11.7 Olay kayıt | ✓ | RotatingFileHandler 10MB×5; audit_log tablosu |
| 11.8 İzleme | ⬜ | Planlı: Prometheus/Grafana (Q3 2026) |
| 11.9 Saat senkronizasyonu | ✓ | macOS NTP; UTC timestamp |
| 11.10 Yazılım kurulum kontrolü | ✓ | `vendor-security-policy.md`; onaylı liste |
| 11.11 Teknik açık yönetimi | ✓ | pip-audit CI; CVE takibi |
| 11.12 Yazılım geliştirme güvenliği | ✓ | OWASP kontrolleri; input validation; ruff lint |

## Bölüm 12 — İletişim Güvenliği

| Kontrol | Durum | Uygulama |
|---|---|---|
| 12.1 Ağ kontrolleri | ✓ | TLS zorunlu (server mod); CORS kısıtlı |
| 12.2 Ağ hizmetleri güvenliği | ✓ | Rate limiting; API key veya JWT |
| 12.3 Ağ ayrımı | ✓ | On-premise: kurum ağında izole |
| 12.4 Filtreleme | ✓ | Path traversal koruması; input validation |

## Bölüm 13 — Tedarikçi İlişkileri

| Kontrol | Durum | Uygulama |
|---|---|---|
| 13.1 Tedarikçi politikası | ✓ | `vendor-security-policy.md` |
| 13.2 Tedarikçi anlaşmaları | ⬜ | Planlı: HuggingFace ToS incelemesi |
| 13.3 Tedarikçi izleme | ✓ | SHA-256 model doğrulama; pip-audit |

## Bölüm 14 — Olay Yönetimi

| Kontrol | Durum | Uygulama |
|---|---|---|
| 14.1 Olay yönetimi prosedürü | ✓ | `incident-response-plan.md` |
| 14.2 Olay bildirimi | ✓ | KVKK 72 saat bildirimi; müşteri bildirimi |
| 14.3 Olay değerlendirme | ✓ | CVSS puanlama; karar ağacı |
| 14.4 Adli analiz | ⬜ | Planlı: log analiz araçları (Q4 2026) |

## Bölüm 15 — İş Sürekliliği

| Kontrol | Durum | Uygulama |
|---|---|---|
| 15.1 İş sürekliliği planı | ✓ | `business-continuity-plan.md` |
| 15.2 BCP tatbikatı | ⬜ | Planlı: Q2 2026 |
| 15.3 ICT hazırlığı | ✓ | RTO ≤ 4h; RPO ≤ 24h |

## Bölüm 16 — Uyumluluk

| Kontrol | Durum | Uygulama |
|---|---|---|
| 16.1 Yasal uyumluluk | ✓ | KVKK; BDDK; VERBİS kaydı |
| 16.2 Fikri mülkiyet | ✓ | Açık kaynak lisans uyumu |
| 16.3 Kayıtların korunması | ✓ | Log rotation; audit log |
| 16.4 Gizlilik | ✓ | `data-residency.md`; DPA şablonu |
| 16.5 Teknik uyumluluk gözden geçirme | ⬜ | Planlı: yıllık pentest (Q3 2026) |

---

## Özet Tablo

| Durum | Kontrol Sayısı |
|---|---|
| ✓ Uygulandı | 45 |
| ⬜ Planlandı | 9 |
| ✗ Kapsam dışı | 0 |
| — Geçerli değil | 4 |
| **Toplam** | **58** |

**Uyum oranı (planlananlar dahil):** %93 | **Sadece uygulananlar:** %78

---

*Bir sonraki gözden geçirme: Q2 2026 (iç tetkik öncesi)*
