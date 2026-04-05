---
title: Tedarikçi Güvenlik Politikası
version: 1.0
date: 2026-04-05
owner: Bilgi Güvenliği
standard: ISO 27001:2022 / A.5.19, A.5.20, A.5.21, A.5.22
---

# Tedarikçi Güvenlik Politikası

## 1. Amaç ve Kapsam

Bu politika, VoiceFlow'un bağımlı olduğu dış yazılım ve hizmet tedarikçilerinin güvenlik risklerini yönetir. VoiceFlow'un on-premise mimarisi gereği müşteri verisi hiçbir dış sisteme gönderilmez; bu durum tedarikçi riskini önemli ölçüde sınırlar.

## 2. Temel Güvenlik Prensibi

**VoiceFlow, üretim ortamında sıfır bulut bağımlılığı prensibiyle çalışır.** Tüm konuşma işleme, transkripsiyon ve AI düzeltme işlemleri müşterinin kendi donanımında gerçekleşir. Tedarikçiler yalnızca geliştirme ve kurulum aşamasında devreye girer.

## 3. Tedarikçi Envanteri ve Risk Değerlendirmesi

### 3.1 Açık Kaynak Runtime Bağımlılıkları

| Tedarikçi | Bileşen | Risk Seviyesi | Veri Teması |
|---|---|---|---|
| Python (PSF) | Interpreter, stdlib | Düşük | Yok — çalışma zamanı |
| FastAPI / Uvicorn | HTTP framework | Düşük | Yok — kod kütüphanesi |
| mlx / mlx-lm | Apple MLX ML framework | Düşük | Yok — yerel hesaplama |
| mlx-whisper | Transkripsiyon motoru | Düşük | Yok — yerel hesaplama |
| aiosqlite / SQLCipher | Veritabanı | Düşük | Yerel DB dosyası — şifreli |
| ChromaDB | Vektör veritabanı | Düşük | Yok — yerel storage |
| Homebrew | Paket yöneticisi | Düşük | Yok — kurulum aracı |

**Risk değerlendirmesi:** Açık kaynak bağımlılıklar üretim verisine erişmez. Güvenlik yamaları için paket güncellemeleri takip edilir.

**Kontroller:**
- `requirements.txt` / `pyproject.toml`'da sürümler sabitlenir
- Bağımlılık güvenlik taraması: `pip audit` (CI/CD'de)
- Kritik CVE bildirimlerinde 72 saat içinde güncelleme

---

### 3.2 Hugging Face (Model İndirme)

| Özellik | Değer |
|---|---|
| Risk Seviyesi | Düşük |
| Veri Teması | Yok — yalnızca model indirme |
| Kullanım Amacı | Whisper ve Qwen model ağırlıklarının kurulum sırasında indirilmesi |
| Üretim Bağımlılığı | Hayır — indirme tamamlandıktan sonra internet bağlantısı gerekmez |

**Açıklama:** HF yalnızca ilk kurulum veya model güncellemesi sırasında kullanılır. Üretim transkripsiyon işlemi için internet bağlantısı gerekmez. Müşteri verisi Hugging Face'e gönderilmez.

**Kontroller:**
- Model hash doğrulaması kurulum sonrası yapılır
- Airgapped ortamlarda model dosyaları USB/dahili ağ üzerinden dağıtılabilir
- `HF_TOKEN` yalnızca kurulum makinasında saklanır, üretim sistemine geçmez

---

### 3.3 GitHub (Kod Deposu)

| Özellik | Değer |
|---|---|
| Risk Seviyesi | Orta |
| Veri Teması | Kaynak kodu — üretim verisi yok |
| Kullanım Amacı | Kaynak kod yönetimi, CI/CD tetikleyicisi |

**Kontroller:**
- Üretim veritabanı, `.env` dosyaları ve model ağırlıkları repoya commit edilmez (`.gitignore`)
- Branch koruma kuralları (main branch için PR zorunlu)
- GitHub Actions'ta gizli anahtarlar GitHub Secrets üzerinden yönetilir
- On-premise kurulumlar için repo erişimi kısıtlanabilir (private repo)

---

### 3.4 RunPod (GPU Eğitim Altyapısı)

| Özellik | Değer |
|---|---|
| Risk Seviyesi | Orta — üretim için Düşük |
| Veri Teması | Eğitim verisi (anonim metin) — üretim transkripti değil |
| Kullanım Amacı | Yalnızca AI model fine-tuning (geliştirme aşaması) |
| Üretim Bağımlılığı | **Hayır** — üretim sisteminde kullanılmaz |

**Açıklama:** RunPod yalnızca VoiceFlow'un kendi AI modellerini eğitmek için kullanılır. Müşteriye ait ses kayıtları veya transkriptler RunPod'a gönderilmez. Eğitim verisi anonim metin çiftlerinden oluşur.

**Kontroller:**
- RunPod pod'ları eğitim bitince durdurulur (maliyet + güvenlik)
- Eğitim verisi kişisel veri içermez
- API anahtarları `.env` dosyasında saklanır, CI pipeline'a açık değil

---

### 3.5 Apple (macOS / Xcode / Swift)

| Özellik | Değer |
|---|---|
| Risk Seviyesi | Düşük |
| Veri Teması | İşletim sistemi entegrasyonu |
| Kullanım Amacı | macOS istemci uygulaması çalışma ortamı |

**Kontroller:**
- Uygulama sandbox kısıtlamaları macOS tarafından uygulanır
- Erişilebilirlik izni kullanıcı onayı gerektirir
- Ses girişi yalnızca kayıt modunda aktif (izin göstergesi)

## 4. Tedarikçi Değerlendirme Kriterleri

Yeni bir tedarikçi veya bağımlılık eklenirken aşağıdaki sorular yanıtlanır:

1. Üretim müşteri verisi bu tedarikçiye ulaşır mı?
2. Tedarikçinin güvenlik sertifikası var mı? (ISO 27001, SOC 2)
3. Bağımlılık aktif olarak bakımı yapılan açık kaynak mu?
4. Son 12 ayda kritik CVE var mı, kaç günde yayımlandı?
5. Airgapped ortamda çalışabilir mi?

**Veto kriteri:** Üretim ortamında müşteri verisi işleyen tedarikçi için SOC 2 Type II veya ISO 27001 sertifikası zorunludur.

## 5. Tedarikçi Takip ve Gözden Geçirme

- Tedarikçi listesi yılda bir güncellenir
- Yeni bağımlılık eklemesi teknik lider onayı gerektirir
- `pip audit` bulguları aylık raporlanır
- Orta/yüksek riskli tedarikçi değişikliği CISO'ya bildirilir

**Onay:** Bilgi Güvenliği Sorumlusu — 2026-04-05
