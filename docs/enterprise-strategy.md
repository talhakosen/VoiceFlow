# VoiceFlow — Kurumsal Strateji

## Ürün Vizyonu

Kurumsal mühendisler ve ofis çalışanları için şirkete özel bağlam anlayan,
tamamen şirket içinde çalışan sesli metin dönüştürme platformu.

**Temel fark:** Genel transkripsiyon aracı değil — şirketin kod tabanını,
terminolojisini, iletişim stilini öğrenen bağlam-duyarlı asistan.

---

## Hedef Müşteri

- Türkiye'deki büyük kurumsal şirketler (100–5000 çalışan)
- Teknoloji, finans, telecom sektörü
- Örnekler: Akbank, Türkcell, Garanti BBVA, Trendyol, Yapı Kredi
- Mac kullanan mühendis ekipleri (veri egemenliği hassasiyeti yüksek)

---

## Ürün Paketleri

### Engineering Suite
Yazılım ekipleri için:
- Git repo indexleme → şirkete özel teknik terminoloji
- Teknik terimleri korur (sınıf, fonksiyon, servis isimleri değişmez)
- Çıktı: kod yorumu, PR açıklaması, teknik dokümantasyon

### Office Suite
Yönetici / proje yöneticisi / satış için:
- Email taslağı (alıcı + konuya göre ton)
- Resmi Türkçe, kısaltma açma
- Toplantı notu, durum raporu formatları

---

## Deployment Modeli

### Satış Süreci
1. Demo (RunPod'da server mode, ~1.5s yanıt)
2. Pilot (10–20 kişi, 1 ay ücretsiz)
3. Kurulum (Docker Compose → müşteri GPU sunucusu)
4. Lisans sözleşmesi

### Teknik Kurulum
```
Müşteri sağlar:
├── Ubuntu sunucu (min. RTX 4090, 24GB VRAM)
├── Şirket VPN erişimi
└── Docker + NVIDIA Container Toolkit

Biz sağlarız:
├── Docker Compose paketi (API + Whisper + LLM + Vector DB)
├── Mac app (DMG — tüm mühendislere)
├── Kurulum + konfigürasyon
└── İlk knowledge base indexleme
```

**Dağıtım:** App Store YOK — DMG, doğrudan şirketlere.
App Store sandbox global hotkey + auto-paste'i engeller.

---

## Fiyatlandırma

- Setup: $2,000–5,000 (sunucu kurulumu + eğitim)
- Yıllık: $200–400 / kullanıcı
- 50 kullanıcı örnek: Setup $3,000 + $15,000/yıl = **$18,000 Yıl 1**

---

## Demo Altyapısı (RunPod)

**RTX 4090, mesai saatleri modu ~$95/ay**
- faster-whisper large-v3 (CUDA)
- Ollama + Qwen 2.5 7B
- Beklenen: ~1–1.5s uçtan uca

Docker + RunPod deployment → Phase 5'te (şimdi lokal geliştirme öncelikli).

---

## Development Roadmap

### ✅ Phase 0 — Demo Altyapısı
- [x] BACKEND_MODE env flag (local/server)
- [x] faster-whisper entegrasyonu (numpy→BytesIO adapter)
- [x] Ollama HTTP client (correct_async — MLX executor'ı bloklamaz)
- [x] API key auth middleware (X-Api-Key, local'de no-op)
- [x] 0.0.0.0 bind (server mode)
- [x] Mac app: server URL + API key (Settings window)
- [x] AppDelegate: server modunda local backend başlatmaz

### ✅ Phase 0.5 — Architecture Refactor
- [x] Backend: Layered Architecture (core/interfaces → services → api)
- [x] Backend: RecordingService DI (testable, mock inject edilebilir)
- [x] Backend: routes.py → sadece HTTP (~100 satır)
- [x] Swift: MVVM + @Observable (AppViewModel)
- [x] Swift: BackendServiceProtocol (loose coupling)
- [x] Swift: MenuBarController → sadece UI (~200 satır, eskiden 600)

### ✅ Phase 1 — Foundation
- [x] SQLite persistent storage (aiosqlite, ~/.voiceflow/voiceflow.db)
- [x] Mod sistemi: General / Engineering / Office (mode-aware LLM prompts)
- [x] Onboarding sihirbazı (NavigationStack, 3 adım, ilk açılış)
- [x] Kullanıcı profili (UUID, ad, departman — Settings panel)
- [x] X-User-ID header → transcriptions.user_id
- [x] GET/DELETE /api/history endpoint'leri

### 🔲 Phase 2 — Context Engine
- [ ] ChromaDB multi-tenant (tenant=company_id)
- [ ] Local embedding model (MiniLM veya MLX muadili)
- [ ] Dosya ingestion pipeline (kod, dokümantasyon)
- [ ] RAG: retrieval → LLM prompt injection
- [ ] Mac app: knowledge base klasör seçimi UI
- [ ] Kalite testi: 7B + context yeterli mi?

### 🔲 Phase 3 — Engineering Package
- [ ] Git repo indexleme (FSEvents ile otomatik)
- [ ] Teknik terminoloji çıkarma (class/func/servis isimleri)
- [ ] Engineering prompt template'leri
- [ ] Çıktı: kod yorumu, PR açıklaması, ticket

### 🔲 Phase 4 — Office Package
- [ ] Alıcı profili sistemi
- [ ] Email ton belirleme (formal/informal/teknik)
- [ ] Mail.app entegrasyonu (AppleScript)
- [ ] Şirket template library

### 🔲 Phase 5 — Enterprise Distribution
- [ ] Developer ID imzalama + notarization (mevcut Apple hesabı yeterli)
- [ ] DMG paketleme → şirket web sitesi
- [ ] Docker Compose paketi (FastAPI + Ollama + faster-whisper)
- [ ] RunPod deploy, RTX 4090, <2s test
- [ ] Admin dashboard
- [ ] Offline lisanslama
- [ ] IT kurulum dokümantasyonu

---

## Rekabet Avantajları

| Özellik | VoiceFlow | Whisper (generic) | Cloud AI |
|---|---|---|---|
| Tamamen on-premise | ✅ | ✅ | ❌ |
| Türkçe optimize | ✅ | Orta | Orta |
| Şirkete özel context | ✅ (Phase 2) | ❌ | Kısıtlı |
| Veri egemenliği garantisi | ✅ | ✅ | ❌ |
| Mac native UX + auto-paste | ✅ | ❌ | ❌ |
| SOLID, test edilebilir kod | ✅ | ❌ | — |

---

## Bilinen Riskler

1. **Satış döngüsü:** Türk kurumsal müşteride 3–9 ay
2. **IT onayı:** GPU sunucu kurulumu güvenlik onayı gerektirir
3. **LLM kalitesi:** 7B Türkçe context'te yeterli mi? → pilot ile doğrulanacak
4. **Donanım:** Müşteride GPU yoksa ek maliyet/gecikme
