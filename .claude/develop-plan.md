# VoiceFlow — Development Plan

## Phase 0: Demo Hazırlığı (Hedef: RunPod'da <2s yanıt)

- [ ] Backend: `BACKEND_MODE` env flag (local/server)
- [ ] Backend: `faster-whisper` entegrasyonu — **numpy array → BytesIO adapter zorunlu**
      `WhisperModel("large-v3", device="cuda", compute_type="float16")`
      `vad_filter=True` ekle (sessizlik filtresi)
- [ ] Backend: Ollama HTTP client — **OpenAI-compat `/v1/chat/completions`** kullan
      mlx-lm da aynı endpoint'i sunuyor → tek client, iki mod
      `keep_alive=-1` ile model GPU'da sürekli yüklü
- [ ] Backend: API key auth middleware (`X-API-Key` header)
- [ ] Backend: `0.0.0.0` bind (server mode için)
- [ ] Mac app: server URL configurable (`@AppStorage("serverURL")`)
- [ ] Mac app: API key ayarı
- [ ] Docker: `Dockerfile` + `docker-compose.yml` (FastAPI + Ollama + faster-whisper)
- [ ] RunPod: deploy et, RTX 4090, uçtan uca test (<2s hedef)

## Phase 1: Foundation (Kurumsal Kullanıma Hazır)

- [ ] SQLite persistent storage (history, config)
- [ ] Kullanıcı profili (ad, rol, departman, mod)
- [ ] Onboarding sihirbazı (Mac app, ilk açılış)
- [ ] Settings panel (SwiftUI window)
- [ ] Mod sistemi: Engineering / Office / General
- [ ] Audit log (sunucu tarafı, kim/ne zaman/kaç saniye)
- [ ] Multi-user desteği (user_id per request)

## Phase 2: Context Engine (Ürünün Kalbi)

- [ ] ChromaDB entegrasyonu — **multi-tenant hazır**: `PersistentClient(tenant=company_id, database=dept)`
      Şirket izolasyonu için ayrı tenant/database, ek kod gerekmez
- [ ] Embedding model (local, hızlı — MiniLM veya benzeri)
- [ ] Dosya ingestion pipeline (kod, dokümantasyon, email template)
- [ ] RAG retrieval → LLM prompt injection
- [ ] Mac app: knowledge base klasör seçimi UI
- [ ] Bağlam inject edilince kalite testi (7B model yeterli mi?)

## Phase 3: Engineering Package

- [ ] Git repo indexleme (otomatik, FSEvents ile değişiklik takibi)
- [ ] Teknik terminoloji çıkarma (class/func/servis isimleri)
- [ ] Engineering prompt template'leri
- [ ] Çıktı formatları: kod yorumu, PR açıklaması, ticket

## Phase 4: Office Package

- [ ] Alıcı profili sistemi
- [ ] Email ton belirleme (formal/informal/teknik)
- [ ] Mail.app entegrasyonu (AppleScript)
- [ ] Şirket template library import

## Phase 5: Enterprise Distribution

- [ ] Code signing + notarization (Apple Developer Program)
- [ ] DMG paketleme
- [ ] Docker Compose kurulum paketi (şirket IT için)
- [ ] Admin dashboard (kullanıcı yönetimi)
- [ ] Offline lisanslama (license key doğrulama)
- [ ] Kurulum dokümantasyonu

---

## Şu An Çalışan (v0.1)
- Fn double-tap hotkey ile ses kaydı
- mlx-whisper ile Türkçe/İngilizce transkripsiyon
- Qwen 7B ile isteğe bağlı Türkçe düzeltme
- Auto-paste (Cmd+V)
- Menu bar history (son 50, RAM'de)
- Tüm işlem local (Apple Silicon MLX)

## Mimari Kararlar
- **Local-first, server optional:** Aynı Mac app her iki modda çalışır, sadece URL değişir
- **Açık kaynak modeller:** Cloud API yok — Whisper, Qwen/Llama self-hosted
- **MLX (Mac) + NVIDIA (server):** İki farklı inference engine, env ile seçilir
- **Birleşik LLM client:** mlx-lm server + Ollama ikisi de `/v1/chat/completions` sunuyor
  → tek `httpx` client, iki mod. vLLM'e geçiş de trivial.
- **faster-whisper input:** numpy array değil BytesIO — `soundfile` ile dönüştür
- **Ollama keep_alive=-1:** Model GPU'da sürekli yüklü, cold start yok
- **ChromaDB multi-tenancy:** `tenant=company_id` — şirket izolasyonu built-in
- **Docker Compose:** Şirket IT kurulumu basit olmalı
- **Mac App Store değil, DMG:** Sandbox global hotkey + paste'i kısıtlar
- **7B minimum LLM:** 1.5B ve 3B Türkçe'de hallüsinasyon yapıyor (doğrulandı)
- **RunPod demo:** RTX 4090, mesai saatleri modu, ~$95/ay
