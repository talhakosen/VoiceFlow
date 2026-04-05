---
title: Veri Sınıflandırma Politikası
version: 1.0
date: 2026-04-05
owner: Bilgi Güvenliği
standard: ISO 27001:2022 / A.5.12
---

# Veri Sınıflandırma Politikası

## 1. Amaç ve Kapsam

Bu politika, VoiceFlow sistemlerinde işlenen tüm verilerin doğru şekilde sınıflandırılmasını, etiketlenmesini ve korunmasını sağlar. Müşteri kurumun on-premise dağıtımındaki tüm bileşenleri kapsar: Python/FastAPI backend, SQLite veritabanı, macOS Swift istemcisi ve AI modeller.

## 2. Sınıflandırma Seviyeleri

### 2.1 GİZLİ (Confidential)

Yetkisiz erişimin kurumsal veya kişisel zarar doğurabileceği veriler.

**VoiceFlow örnekleri:**
- Kullanıcı transkriptleri (konuşma kayıtları ve metinleri)
- Ses kayıt dosyaları (geçici buffer dahil)
- Kullanıcı kimlik bilgileri ve API anahtarları
- Müşteri kurumun bilgi bankası (ChromaDB içeriği)
- SQLite veritabanı (`voiceflow.db`) — hassas transkript geçmişi

**İşleme kuralları:**
- SQLCipher ile şifreli olarak saklanır (AES-256)
- Ağ üzerinden yalnızca TLS 1.2+ ile taşınır
- Ekrana yansıtma ve paylaşım yasaktır
- Saklama süresi sonunda güvenli silme (DoD 5220.22-M)

---

### 2.2 KISITLI (Restricted)

Yalnızca belirli roller tarafından erişilebilir operasyonel veriler.

**VoiceFlow örnekleri:**
- Sistem logları (`/tmp/voiceflow.log`, uygulama hata logları)
- Backend yapılandırma dosyaları (`config.yaml`, `.env`)
- Erişim kontrol listesi ve kullanıcı rolleri
- Performans metrikleri ve kullanım istatistikleri

**İşleme kuralları:**
- Yalnızca sistem yöneticisi ve yetkili IT erişebilir
- Log dosyaları 90 gün sonra silinir
- `.env` dosyası versiyon kontrolüne dahil edilmez (`.gitignore`)

---

### 2.3 DAHİLİ (Internal)

Kurum içinde serbestçe paylaşılabilen ancak dışarıya çıkmaması gereken veriler.

**VoiceFlow örnekleri:**
- Fine-tuned AI model ağırlıkları (`ml/qwen/adapters_mlx/`, `ml/whisper/models/`)
- Geliştirme dokümantasyonu ve mimari diyagramlar
- Kurulum ve dağıtım kılavuzları
- İç iletişimler ve proje notları

**İşleme kuralları:**
- Kurum içi sistemlerde kısıtlama olmadan paylaşılabilir
- Dış taraflarla NDA kapsamında paylaşılabilir
- Model ağırlıkları yetkisiz replikasyona karşı korunur

---

### 2.4 KAMUYA AÇIK (Public)

Kamuya açıklanması onaylanmış veriler.

**VoiceFlow örnekleri:**
- API endpoint belgeleri (dağıtılan sürüm için)
- Ürün tanıtım materyalleri
- Açık kaynak bağımlılık lisans listesi
- Genel teknik gereksinimler

**İşleme kuralları:**
- Yayınlamadan önce onay alınmalıdır
- Gizli/kısıtlı içerik gömülü olmamalıdır

## 3. Etiketleme Standardı

| Sınıf | Dosya Başlığı | Metadata Etiketi | Renk Kodu |
|---|---|---|---|
| Gizli | `[GİZLİ]` | `classification: confidential` | Kırmızı |
| Kısıtlı | `[KISITLI]` | `classification: restricted` | Turuncu |
| Dahili | `[DAHİLİ]` | `classification: internal` | Sarı |
| Kamuya Açık | `[AÇIK]` | `classification: public` | Yeşil |

VoiceFlow dokümantasyon dosyaları frontmatter'da `classification` alanı içermelidir.

## 4. Özel Durumlar

**Transkript verileri:** KVKK kapsamında kişisel veri sayılır. Veri sahibi rızası alınmadan 3. taraflarla paylaşılamaz. Kurumun saklama politikasına göre silinir.

**AI model ağırlıkları:** Ticari sır niteliğinde. On-premise dağıtımda müşteriye teslim edilmez; kurulum sırasında cihaza yüklenir ve erişim kilitleniir.

**Ses buffer'ları:** Transkripsiyon sonrası derhal bellekten silinir. Diske yazılmaz.

## 5. İhlal Yükümlülükleri

Sınıflandırma ihlali tespit eden personel 24 saat içinde Bilgi Güvenliği birimine bildirir. Gizli/Kısıtlı veri sızıntısı KVKK md.12 kapsamında 72 saat içinde Kişisel Verileri Koruma Kurumu'na raporlanır.

## 6. Gözden Geçirme

Bu politika yılda bir veya önemli sistem değişikliklerinde güncellenir.

**Onay:** Bilgi Güvenliği Sorumlusu — 2026-04-05
