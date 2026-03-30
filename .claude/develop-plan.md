# VoiceFlow — Development Plan

---

## Şu An Çalışan (v0.2)

- Fn double-tap hotkey ile ses kaydı
- mlx-whisper ile Türkçe/İngilizce transkripsiyon
- Qwen 7B ile isteğe bağlı Türkçe düzeltme (3 mod: general/engineering/office)
- Auto-paste (Cmd+V)
- SQLite persistent history (~/.voiceflow/voiceflow.db)
- Kullanıcı profili (UUID, ad, departman)
- Knowledge Base (ChromaDB RAG — lazy load, MiniLM embeddings)
- Local mode (MLX/Mac) + Server mode (faster-whisper + Ollama)
- API key auth middleware
- Layered backend (HTTP → RecordingService → ABCs → Impl → SQLite)
- MVVM + Protocol DI (Swift)

---

## KATMAN 1 — Çekirdek İyileştirme (v0.3)

> Amaç: Mevcut özelliklerin polish'i. Kullanırken "bu sinir bozucu" dedirten şeyleri kapat.
> Ön koşul yok — hemen başlanabilir.

### 1.1 UI/UX Yenileme

- [DONE 2026-03-30] **Menü sadeleştirme** — Wispr Flow gibi minimal:
      Sadece: Status | Toggle Recording | Force Stop | ─ | Settings | Quit
      Dil, mod, correction → Settings'e taşı

- [DONE 2026-03-30] **Settings penceresi — 2-panel yeniden tasarım** (Wispr Flow mimarisi):
      Sol nav: General | Recording | Knowledge Base | Account | About
      Sağ content:
        - General: shortcut (fn), dil seçimi, ses efektleri
        - Recording: mod (general/engineering/office), LLM correction toggle, mikrofon
        - Knowledge Base: klasör seç, index durumu, chunk sayısı, temizle
        - Account: ad, departman, kullanıcı ID
        - About: versiyon, backend durumu, restart/hard reset

- [DONE 2026-03-30] **Recording overlay — floating pill** (Wispr Flow'un "Flow bar"ı gibi):
      Kayıt başlayınca ekranın altında/ortasında küçük koyu pill çıkır
      İçinde sadece waveform animasyonu
      Kayıt bitince kaybolur — hiçbir şey yapıştırana kadar

- [DONE 2026-03-30] **Onboarding yenileme** — mevcut 3-adım yeterli, sadece yeni Settings yapısına uyarla

### 1.2 Backend Kararlılık

- [DONE 2026-03-30] **Phase 2 tamamlama** — ChromaDB entegrasyonu tam test et:
      Klasör indexleme çalışıyor mu? ✓ (38 chunk)
      RAG retrieval LLM'e doğru inject ediliyor mu? ✓ (recording.py pipeline)
      Boş KB'de retrieval atlama çalışıyor mu? ✓ (is_empty guard)

- [DONE 2026-03-30] **Dictionary (Kişisel Sözlük)** — Wispr Flow'daki gibi:
      Kullanıcı özel kelimeler/jargon ekleyebilir (şirket adları, kısaltmalar)
      Backend: SQLite'a `user_dictionary` tablosu
      Whisper post-processing: kelime düzeltme geçişi
      Mac app: Settings → Dictionary section

- [DONE 2026-03-30] **Snippets (Sesli Şablonlar)**:
      "personal email" deyince → email adresi açılır
      SQLite: `snippets` tablosu (trigger_phrase → expansion)
      Mac app: Settings → Snippets section
      Backend: transkript sonrası snippet match → expand

- [DONE 2026-03-30] **Ses efektleri** — kayıt başlama/bitme sesi (system sound veya custom)

---

## KATMAN 2 — Kurumsal Altyapı (v0.4)

> Amaç: Büyük şirkete satış için şart olan altyapı. Auth, tenant izolasyonu, admin panel.
> Ön koşul: Katman 1 tamamlanmış olmalı.

### 2.1 Auth Sistemi

- [ ] **Backend: email/şifre login**:
      `POST /auth/register` — kullanıcı oluştur
      `POST /auth/login` → JWT token döner
      `POST /auth/refresh` → token yenile
      SQLite: `users` tablosu (id, email, password_hash, tenant_id, role)
      JWT middleware: tüm `/api/*` endpoint'leri için

- [ ] **Tenant izolasyonu**:
      Her şirket = ayrı tenant_id
      ChromaDB: `tenant=tenant_id` (zaten hazır)
      SQLite: tüm sorgularda `WHERE tenant_id = ?` filtresi
      Transcription history, dictionary, snippets — tenant bazlı izole

- [ ] **Roller**: superadmin | admin | member
      Admin: kullanıcı ekle/çıkar, istatistik görsün
      Member: sadece kendi transkriptleri

- [ ] **Mac app: Login ekranı**:
      İlk açılışta email/şifre formu (onboarding'in önünde)
      JWT token Keychain'de sakla
      Her API isteğine `Authorization: Bearer <token>` header
      Token expire olunca otomatik logout

### 2.2 Admin Panel (Web)

- [ ] **Basit web UI** (FastAPI + Jinja2 veya ayrı React):
      `/admin` — sadece admin rolü erişebilir
      Kullanıcı listesi: ad, email, rol, son aktivite, kelime sayısı
      Kullanıcı davet et (email ile)
      Kullanıcı deaktive et
      Tenant genelinde istatistikler (toplam transkript, kelime, aktif kullanıcı)

- [ ] **Usage dashboard**:
      Günlük/haftalık/aylık aktif kullanıcı
      En çok kullanılan mod (general/engineering/office)
      Ortalama WPM
      Knowledge Base boyutu

### 2.3 Güvenlik & Uyumluluk

- [ ] **KVKK/BDDK hazırlık belgesi** — "Veriler nerede saklanır?" dokümanı
- [ ] **Data at rest encryption** — SQLite şifreleme (SQLCipher)
- [ ] **Audit log** — kim ne zaman ne yaptı (admin sildi, config değiştirdi)
- [ ] **Veri silme API** — `DELETE /admin/users/:id/data` (KVKK gereği)

---

## KATMAN 3 — Ürün Farklılaştırması (v0.5+)

> Amaç: Wispr Flow'dan ayrışmak, Türkiye kurumsal pazarına özgü değer.
> Ön koşul: Katman 2 tamamlanmış, ilk müşteri demosu yapılmış olmalı.

### 3.1 Kurumsal Özelleştirme

- [ ] **Style/ton per-context** (Wispr Flow'daki gibi):
      Farklı uygulamalar için farklı ton: Mail → formal, Slack → casual, Terminal → teknik
      Mac app: aktif uygulamayı tespit et (NSWorkspace), ton otomatik seç
      Admin: şirket genelinde varsayılan ton politikası

- [ ] **Şirket template library**:
      Admin upload: şirket içi email şablonları, rapor formatları
      Knowledge Base'e otomatik index
      Kullanıcılar sesle şablon çağırabilir

- [ ] **Gamification**:
      Haftalık streak, kelime istatistikleri (Home ekranı)
      "Bu hafta X kelime dikte ettin" bildirimi
      Departman sıralaması (opsiyonel, admin açar/kapar)

### 3.2 Engineering Package (Derinleştirme)

- [ ] Git repo indexleme (otomatik, FSEvents ile değişiklik takibi)
- [ ] Teknik terminoloji çıkarma (class/func/servis isimleri → dictionary'e ekle)
- [ ] Çıktı formatları: kod yorumu, PR açıklaması, Jira ticket
- [ ] VS Code / Cursor entegrasyonu (Vibe coding benzeri)

### 3.3 Office Package (Derinleştirme)

- [ ] Alıcı profili sistemi (kişiye göre ton)
- [ ] Mail.app + Outlook entegrasyonu (AppleScript / URL scheme)
- [ ] Toplantı notu formatı (otomatik madde işaretleri, action item çıkarma)

### 3.4 Enterprise Distribution

- [ ] Docker: `Dockerfile` + `docker-compose.yml` (FastAPI + Ollama + faster-whisper)
- [ ] RunPod: RTX 4090 deploy, uçtan uca test (<2s hedef)
- [ ] DMG paketleme + notarization (Developer ID Application)
- [ ] Kurulum dokümantasyonu (IT için — 1 sayfa, adım adım)
- [ ] Offline lisanslama (license key doğrulama)
- [ ] SSO/SAML hazırlığı (Katman 2 auth'un üzerine, büyük kurumlar için)

---

## Mimari Kararlar

- **Local-first, server optional:** Aynı Mac app her iki modda çalışır
- **Açık kaynak modeller:** Cloud API yok — Whisper, Qwen/Llama self-hosted
- **MLX (Mac) + NVIDIA (server):** İki farklı inference engine, env ile seçilir
- **ChromaDB multi-tenancy:** `tenant=company_id` — şirket izolasyonu built-in
- **Mac App Store değil, DMG:** Sandbox global hotkey + paste'i kısıtlar
- **7B minimum LLM:** 1.5B ve 3B Türkçe'de hallüsinasyon yapıyor (doğrulandı)
- **faster-whisper input:** numpy array değil BytesIO — soundfile ile dönüştür
- **Ollama keep_alive=-1:** Model GPU'da sürekli yüklü, cold start yok

---

## Tamamlanan Fazlar

- [DONE] Phase 0: Demo altyapısı (BACKEND_MODE, faster-whisper, Ollama, API key auth)
- [DONE] Phase 0.5: Architecture refactor (layered backend, MVVM Swift)
- [DONE] Phase 1: Foundation (SQLite, mod sistemi, onboarding, kullanıcı profili, history)
- [DONE] Phase 2 (kısmi): Context Engine (ChromaDB RAG, MiniLM, ingestion pipeline, Knowledge Base UI)
