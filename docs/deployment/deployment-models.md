# VoiceFlow — Deployment Modelleri

Müşteri segmentine göre 4 deployment modeli.

---

## Özet

| Model | Hedef Segment | GPU Kimin? | Veri Nerede? | Müşteri İşi |
|---|---|---|---|---|
| **A — On-Premise** | Banka, holding, kamu | Müşteri | Müşteri DC | GPU sunucu + IT ekibi |
| **B — Hibrit** | *(Önerilmez)* | Mac local + cloud LLM | Metin dışarı çıkar | — |
| **C — Tam Local** | KOBİ, bireysel | Mac (Apple Silicon) | Mac'te | DMG kur, kullan |
| **D — Hosted TR** | Orta firma (50-500 kişi) | VoiceFlow | VoiceFlow TR DC | DMG kur, login ol |

---

## Model A: On-Premise (Bankalar, Kamu)

```
[Müşteri Datacenter / VPN]
├── NVIDIA GPU Sunucu (RTX 4090 / A100)
│   └── Docker Compose
│       ├── voiceflow-backend  (FastAPI, uvicorn)
│       ├── ollama             (Qwen 7B adapter)
│       ├── whisper            (voiceflow-whisper-tr-v2)
│       └── volumes: sqlite, config
│
[Müşteri Mac'ler]
└── VoiceFlow.app → Ayarlar → Sunucu Modu → iç IP
```

**Müşteriye ne gider:**
- Docker image (backend + Whisper model + Qwen adapter weights)
- DMG (Mac app)
- Kurulum dokümanı

**Müşteriye ne GİTMEZ:**
- `ml/qwen/data/` (training data) — sadece trained weights
- `ml/whisper/datasets/` (ISSAI, IT dataset)
- Kaynak kod (sadece compiled image)

**KVKK/BDDK:** Tam uyumlu — ses + metin hiç dışarı çıkmaz. BDDK "birincil sistem yurt dışına taşınamaz" kuralına uygun.

**Gereksinimler:**
- Müşteri tarafı: NVIDIA GPU (min RTX 4090, önerilen A100), Docker, iç ağ
- VoiceFlow tarafı: Docker image, kurulum desteği, yıllık lisans + bakım sözleşmesi

**Kurulum akışı:**
1. Müşteri GPU sunucu sağlar (on-prem veya private cloud TR)
2. VoiceFlow Docker image → müşteri registry'sine push veya offline teslim
3. `docker compose up -d`
4. IT admin → `/admin/` web UI → kullanıcı oluştur
5. Mac'lere DMG dağıtılır (MDM veya manuel)
6. Kullanıcı: Ayarlar → Sunucu Modu → şirket sunucu adresi → Login

---

## Model B: Hibrit (Önerilmez)

Whisper local (Mac MLX), LLM correction cloud (RunPod/VoiceFlow sunucu).

**Sorun:** Transkript metin şirket dışına çıkar → KVKK riski. Bankalar kabul etmez. Sadece iç geliştirme/demo için kullanılır.

Mevcut config: `LLM_BACKEND=ollama` + `LLM_ENDPOINT=https://...`

---

## Model C: Tam Local (KOBİ, Bireysel)

```
[Mac — Apple Silicon]
├── VoiceFlow.app
│   ├── Embedded backend (FastAPI, localhost)
│   ├── MLX Whisper (voiceflow-whisper-tr-v2-mlx)
│   └── MLX Qwen 7B 4bit (~4GB RAM)
└── Her şey tek makinede, internet gerekmez
```

**Avantaj:** Sıfır altyapı, sıfır bağımlılık. DMG kur, kullan.

**Dezavantaj:** Her Mac'te ~4GB model, Apple Silicon zorunlu, tek kullanıcı, IT yönetimi yok.

**Hedef:** Freelancer, küçük ofis, bireysel kullanıcı.

Mevcut config: `BACKEND_MODE=local` (varsayılan)

---

## Model D: VoiceFlow Hosted (Orta Firmalar)

```
[VoiceFlow Datacenter — Türkiye]
├── GPU Sunucu(lar)
│   └── Docker Compose (aynı Model A image'ı)
│       ├── voiceflow-backend (multi-tenant)
│       ├── ollama + Qwen 7B
│       ├── whisper
│       └── nginx (TLS, rate limit)
│
├── Tenant: Firma X  ── izole SQLite + config + dictionary
├── Tenant: Firma Y  ── izole SQLite + config + dictionary
└── ...

[Müşteri Mac'ler]
└── VoiceFlow.app → Ayarlar → Sunucu: api.voiceflow.com.tr → Login
```

**Müşteri deneyimi:** DMG kur → sunucu adresi gir → login → kullan. GPU yok, sunucu yok, IT ekibi gerekmiyor.

**VoiceFlow tarafı:**
- Türkiye'de GPU sunucu (Hetzner TR, Türk Telekom DC, veya colocation)
- Multi-tenant izolasyon (JWT + tenant_id, zaten mevcut)
- Bakım, güncelleme, monitoring hep VoiceFlow'da
- Her müşteri ile DPA (Veri İşleme Sözleşmesi) imzalanır

**KVKK:** Uyumlu — veri Türkiye'de, DPA ile. Ancak BDDK kapsamındaki bankalar için yeterli değil (birincil sistem kuralı).

**Gereksinimler:**
- VoiceFlow tarafı: TR datacenter, GPU, SLA, 7/24 monitoring, DPA şablonu
- Müşteri tarafı: Sadece Mac + internet

---

## KVKK / BDDK Karşılaştırma

| | On-Prem (A) | Hosted TR (D) | Local (C) | Cloud ABD (Wispr) |
|---|---|---|---|---|
| Ses verisi nerede? | Müşteri DC | VoiceFlow TR DC | Mac'te | ABD |
| KVKK uyumu | Tam | Tam (DPA ile) | Tam | Sorunlu |
| BDDK uyumu (banka) | Tam | Riskli | N/A | Yasak |
| Veri egemenliği | Müşteri kontrolü | VoiceFlow TR | Kullanıcı | Yok |

---

## Teknik Ortaklık: Tek Image, Çoklu Deploy

Model A ve D **aynı Docker image'ı** kullanır:

```
voiceflow/server:latest
├── FastAPI backend (BACKEND_MODE=server)
├── Whisper model (baked-in veya volume mount)
├── Ollama + Qwen adapter
└── Config: environment variables ile ayrışır
```

Fark sadece:
- **A:** Müşteri kendi sunucusunda çalıştırır
- **D:** VoiceFlow kendi sunucusunda çalıştırır, multi-tenant

---

## Fiyatlandırma (Taslak)

| Tier | Model | Hedef | İçerik |
|---|---|---|---|
| **Free / Starter** | C (local) | Bireysel | Tam local, topluluk destek |
| **Business** | D (hosted) | Orta firma | Hosted TR, kullanıcı başı fiyat, e-posta destek |
| **Enterprise** | A (on-prem) | Banka, holding | On-prem Docker, dedicated destek, SLA, pentest raporu |

---

## Katman 3 TODO (Bu Doküman Kapsamı)

- [ ] Docker Compose tanımı (backend + ollama + nginx)
- [ ] Model weights paketleme scripti
- [ ] DMG notarization (kurumsal dağıtım)
- [ ] Multi-tenant stress test (10-20 concurrent, tek GPU)
- [ ] TR datacenter seçimi ve maliyet analizi
- [ ] DPA şablonu (avukat ile)
- [ ] Onboarding flow (tenant oluştur → admin davet → kullanıcılar)
- [ ] Monitoring stack (uptime, GPU util, latency)
