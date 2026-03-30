# VoiceFlow — Kurumsal Strateji

## Ürün Vizyonu

Kurumsal mühendisler ve ofis çalışanları için şirkete özel bağlam anlayan,
tamamen şirket içinde çalışan sesli metin dönüştürme platformu.

**Temel fark:** Genel bir transkripsiyon aracı değil — şirketin kod tabanını,
terminolojisini, iletişim stilini öğrenen bir asistan.

---

## Hedef Müşteri

### Öncelikli Segment
- Türkiye'deki büyük kurumsal şirketler
- 100–5000 çalışan, teknoloji veya finans sektörü
- Örnekler: Akbank, Türkcell, Garanti BBVA, Yapı Kredi, Trendyol

### Neden Bu Segment?
- Mac kullanımı mühendis ekiplerinde yüksek (doğrulanmış: "çoğu mühendis Mac kullanıyor")
- Veri egemenliği hassasiyeti yüksek — cloud AI kabul etmiyorlar
- Büyük mühendis ekipleri = yüksek per-seat gelir potansiyeli
- Kurumsal satış döngüsü uzun ama sözleşmeler büyük

---

## Ürün Paketleri

### Paket 1: Engineering Suite
**Hedef:** Yazılım geliştirme ekipleri

**Ne yapar:**
- Ses → kod yorumu, PR açıklaması, teknik dokümantasyon
- Şirketin kod tabanını indexler (git repo, README, docstring)
- Teknik terimleri korur (sınıf isimleri, servis isimleri değişmez)
- "Bu fonksiyonu anlat", "PR açıklaması yaz" gibi komutlar

**Gerçek senaryo:** Mühendis kod yazarken düşüncesini konuşuyor →
sistem kod context'ini bilerek düzgün teknik metin üretiyor.

### Paket 2: Office Suite
**Hedef:** Yöneticiler, proje yöneticisi, satış ekibi

**Ne yapar:**
- Ses → email taslağı (alıcıya ve konuya göre ton)
- Şirket email template'lerini öğrenir
- "CEO'ya", "müşteriye", "ekibe" farklı format
- Toplantı notları, durum raporu formatları

---

## Deployment Modeli (Kurumsal)

### Nasıl Satılır?
1. Demo: RunPod'da çalışan sunucu ile gösterim (~1.5s yanıt)
2. Pilot: 10–20 kişilik ekiple 1 ay ücretsiz
3. Kurulum: Müşteri sunucusuna Docker Compose ile deploy
4. Eğitim: IT ekibine ½ günlük teknik onboarding
5. Sözleşme: Yıllık lisans + destek

### Teknik Kurulum Modeli
```
Müşteri sağlar:
├── Ubuntu sunucu (min. RTX 4090, 24GB VRAM)
├── Şirket VPN erişimi
└── Docker + NVIDIA Container Toolkit

Biz sağlarız:
├── Docker Compose paketi (API + LLM + Whisper + Vector DB)
├── Mac app (DMG, tüm mühendislere)
├── Kurulum ve konfigürasyon
└── İlk knowledge base indexleme
```

**Veri garantisi:** Ses verisi ve transkriptler şirket sunucusundan çıkmaz.
Açık kaynak modeller kullanılır (Llama, Qwen) — üçüncü parti API yok.

---

## Fiyatlandırma Modeli

### Per-Seat Lisans (Önerilen)
- Setup ücreti: $2,000–5,000 (bir kez, sunucu kurulumu + eğitim)
- Yıllık lisans: $200–400 / kullanıcı / yıl
- Destek & güncelleme: Yıllık lisansa dahil

**Örnek:** Akbank, 50 mühendis
- Setup: $3,000
- Yıllık: 50 × $300 = $15,000
- **Toplam Yıl 1: $18,000**

### Şirket İçi Sunucu Alternatifleri
Müşterinin GPU sunucusu yoksa:
- Şirket ağında dedicated mini PC + RTX 4090 önerisi (~$3,000–5,000 donanım)
- Kurulum + donanım danışmanlık hizmeti olarak sunulabilir

---

## Demo Altyapısı (RunPod)

Demo için RunPod'da her zaman açık bir sunucu:

**Seçilen yapılandırma:** RTX 4090 (24GB VRAM), Community Cloud

| Kullanım | Maliyet |
|---|---|
| 7/24 açık | ~$270/ay |
| Mesai saatleri (10s/gün, 22gün) | ~$95/ay |
| Spot pricing (kesinti riski var) | ~$50/ay |

**Teknik stack (RunPod):**
- faster-whisper large-v3 (NVIDIA CUDA)
- Ollama + Qwen 2.5 7B (veya Llama 3.1 8B)
- ChromaDB (vector store)
- FastAPI (mevcut backend refactor)

**Beklenen demo hızı:** ~1–1.5 saniye (LAN'da ~0.8s, internette +100ms)

---

## Development Roadmap

### Phase 0 — Demo Hazırlığı (1–2 hafta)
**Amaç:** RunPod'da çalışan server mode backend

- [ ] Backend: server mode flag (0.0.0.0 bind, API key auth)
- [ ] Backend: faster-whisper entegrasyonu (MLX → NVIDIA)
- [ ] Backend: Ollama HTTP client (mlx-lm yerine)
- [ ] Mac app: server URL configurable (hardcoded localhost kalkıyor)
- [ ] RunPod: Docker image hazırla, deploy et
- [ ] Test: uçtan uca <2s yanıt doğrula

### Phase 1 — Foundation (4–5 hafta)
**Amaç:** Bireysel kurumsal kullanıma hazır

- [ ] Persistent storage (SQLite — history, config)
- [ ] Kullanıcı profili (rol, departman, mod)
- [ ] Onboarding sihirbazı (Mac app)
- [ ] Settings panel (SwiftUI)
- [ ] Mod sistemi (Engineering / Office / General)
- [ ] Audit log (sunucu tarafı)

### Phase 2 — Context Engine (6–8 hafta)
**Amaç:** Şirkete özel bağlam — ürünün kalbi

- [ ] ChromaDB entegrasyonu
- [ ] Dosya ingestion pipeline (kod, dokümantasyon)
- [ ] Embedding model (local, fast)
- [ ] RAG retrieval → LLM prompt injection
- [ ] Mac app: knowledge base klasör seçimi UI

### Phase 3 — Engineering Package (4–5 hafta)
- [ ] Git repo indexleme (otomatik, değişiklikleri takip)
- [ ] Teknik terminoloji çıkarma (sınıf, fonksiyon, servis isimleri)
- [ ] Engineering prompt template'leri
- [ ] Kod yorumu, PR açıklaması, ticket formatları

### Phase 4 — Office Package (4–5 hafta)
- [ ] Alıcı profili sistemi (macOS Contacts entegrasyonu)
- [ ] Email ton belirleme (formal/informal/teknik)
- [ ] Mail.app entegrasyonu (AppleScript)
- [ ] Şirket template library import

### Phase 5 — Enterprise Distribution (3–4 hafta)
- [ ] Code signing + notarization (Apple Developer Program)
- [ ] DMG paketleme
- [ ] Docker Compose kurulum paketi
- [ ] Admin dashboard (kullanıcı yönetimi)
- [ ] Lisanslama sistemi (offline doğrulama)
- [ ] Kurulum dokümantasyonu (IT için)

**Toplam tahmini süre: 5–6 ay**

---

## Rekabet Avantajları

| Özellik | VoiceFlow | Whisper (generic) | Cloud AI (Copilot vb.) |
|---|---|---|---|
| Tamamen local/on-premise | ✅ | ✅ | ❌ |
| Türkçe optimize | ✅ | Orta | Orta |
| Şirkete özel context | ✅ (Phase 2) | ❌ | Kısıtlı |
| Veri egemenliği garantisi | ✅ | ✅ | ❌ |
| Mac native UX | ✅ | ❌ | Tarayıcı |
| Auto-paste | ✅ | ❌ | ❌ |
| Kurumsal destek | ✅ | ❌ | ✅ |

---

## Bilinen Riskler

1. **Satış döngüsü:** Türk kurumsal müşterilerde karar süreci uzun (3–9 ay)
2. **IT onayı:** Şirket sunucusuna kurulum IT güvenlik onayı gerektirir
3. **Donanım:** Müşteride GPU sunucu yoksa ek maliyet/gecikme
4. **MLX → NVIDIA geçişi:** Backend refactor iş yükü (Phase 0'da yapılacak)
5. **LLM kalitesi:** 7B model Turkish context'te yeterli mi? → pilot ile doğrulanacak
