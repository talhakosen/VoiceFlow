# VoiceFlow — Development Plan

---

## Şu An Çalışan (v0.3 — Katman 1 + Katman 2 kısmen)

- Fn double-tap hotkey ile ses kaydı
- mlx-whisper ile Türkçe/İngilizce transkripsiyon
- Qwen 7B ile isteğe bağlı Türkçe düzeltme (3 mod: general/engineering/office)
- Auto-paste (Cmd+V)
- SQLite persistent history + tenant izolasyonu
- Kişisel Sözlük (user_dictionary) + Sesli Şablonlar (snippets)
- Knowledge Base (ChromaDB RAG — lazy load, MiniLM embeddings)
- Recording overlay floating pill + ses efektleri
- 2-panel Settings (General/Recording/Dictionary/Snippets/KB/Account/About)
- Local mode (MLX/Mac) + Server mode (faster-whisper + Ollama)
- JWT auth (register/login/refresh) — server mode
- Mac app login ekranı + Keychain token saklama
- Rol sistemi (superadmin/admin/member) + /admin/* endpoint'leri
- Admin web UI (Jinja2 Bootstrap 5) + usage dashboard (/admin/)
- Audit log (append-only SQLite) + KVKK veri silme API
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

- [DONE 2026-03-30] **Backend: email/şifre login**:
      `POST /auth/register` — kullanıcı oluştur
      `POST /auth/login` → JWT token döner
      `POST /auth/refresh` → token yenile
      SQLite: `users` tablosu (id, email, password_hash, tenant_id, role)
      JWT middleware: tüm `/api/*` endpoint'leri için

- [DONE 2026-03-30] **Tenant izolasyonu**:
      Her şirket = ayrı tenant_id
      SQLite: transcriptions/dictionary/snippets tüm sorgularda tenant_id filtresi
      JWT payload → request.state.tenant_id → DB sorgularına geçilir

- [DONE 2026-03-30] **Roller**: superadmin | admin | member
      Admin: kullanıcı ekle/çıkar, istatistik görsün
      Member: sadece kendi transkriptleri

- [DONE 2026-03-30] **Mac app: Login ekranı**:
      İlk açılışta email/şifre formu (onboarding'in önünde)
      JWT token Keychain'de sakla (SecItemAdd)
      Her API isteğine `Authorization: Bearer <token>` header
      Token expire olunca otomatik refresh, başarısızsa logout

### 2.2 Admin Panel (Web)

- [DONE 2026-03-30] **Basit web UI** (FastAPI + Jinja2 veya ayrı React):
      `/admin` — sadece admin rolü erişebilir
      Kullanıcı listesi: ad, email, rol, son aktivite, kelime sayısı
      Kullanıcı davet et (email ile)
      Kullanıcı deaktive et
      Tenant genelinde istatistikler (toplam transkript, kelime, aktif kullanıcı)

- [DONE 2026-03-30] **Usage dashboard**:
      Günlük/haftalık/aylık aktif kullanıcı
      En çok kullanılan mod (general/engineering/office)
      Ortalama WPM
      Knowledge Base boyutu

### 2.3 Güvenlik & Uyumluluk

- [ ] **KVKK/BDDK hazırlık belgesi** — "Veriler nerede saklanır?" dokümanı
- [ ] **Data at rest encryption** — SQLite şifreleme (SQLCipher)
- [DONE 2026-03-30] **Audit log** — login, config_changed, history_cleared, user_data_deleted events; append-only SQLite tablo
- [DONE 2026-03-30] **Veri silme API** — `DELETE /admin/users/:id/data` (KVKK gereği) — transkript+sözlük+snippet+hesap kalıcı silme

---

## KATMAN 3 — Ürün Farklılaştırması (v0.5+)

> Amaç: Wispr Flow'dan ayrışmak, Türkiye kurumsal pazarına özgü değer.
> Ön koşul: Katman 2 tamamlanmış, ilk müşteri demosu yapılmış olmalı.

### 3.1 Kurumsal Özelleştirme

- [DONE 2026-03-30] **Style/ton per-context** (Wispr Flow'daki gibi):
      Farklı uygulamalar için farklı ton: Mail → formal, Slack → casual, Terminal → teknik
      Mac app: aktif uygulamayı tespit et (NSWorkspace), ton otomatik seç
      Bundle ID → tone mapping (10 app), X-Active-App header

- [ ] **Şirket template library**:
      Admin upload: şirket içi email şablonları, rapor formatları
      Knowledge Base'e otomatik index
      Kullanıcılar sesle şablon çağırabilir

- [ ] **Gamification**:
      Haftalık streak, kelime istatistikleri (Home ekranı)
      "Bu hafta X kelime dikte ettin" bildirimi
      Departman sıralaması (opsiyonel, admin açar/kapar)

### 3.2 Engineering Package (Derinleştirme)

- [DONE 2026-03-30] Git repo indexleme: ingest_git_repo() — git log + ingest_folder
- [DONE 2026-03-30] Teknik terminoloji çıkarma: extract_symbols() regex, POST /api/engineering/extract-symbols
- [DONE 2026-03-30] Çıktı formatları: output_format config (prose/code_comment/pr_description/jira_ticket)
- [DONE 2026-03-30] VS Code entegrasyonu: docs/vscode-integration.md URL scheme dökümantasyonu

### 3.3 Office Package (Derinleştirme)

- [ ] Alıcı profili sistemi (kişiye göre ton)
- [ ] Mail.app + Outlook entegrasyonu (AppleScript / URL scheme)
- [ ] Toplantı notu formatı (otomatik madde işaretleri, action item çıkarma)

### 3.4 Enterprise Distribution

- [DONE 2026-03-30] Docker: `Dockerfile` + `docker-compose.yml` (FastAPI + Ollama + faster-whisper) — non-root, GPU, env secrets, healthcheck
- [DONE 2026-03-31] RunPod: RTX 4090 deploy, Ollama qwen2.5:7b — Settings'ten Local/Cloud/Alibaba toggle
- [DONE 2026-03-31] Alibaba DashScope (qwen-max) — 3. LLM backend seçeneği, dashscope-intl endpoint, API key .env'den
- [DONE 2026-03-31] Backend restart sonrası correction toggle state otomatik gönderilir (AppViewModel.restartBackend fix)
- [ ] DMG paketleme + notarization (Developer ID Application)
- [ ] Kurulum dokümantasyonu (IT için — 1 sayfa, adım adım)
- [ ] Offline lisanslama (license key doğrulama)
- [ ] SSO/SAML hazırlığı (Katman 2 auth'un üzerine, büyük kurumlar için)

---

## KATMAN 4 — Correction Kalitesi & Fine-Tuning (v0.6+)

> Amaç: Wispr Flow kalitesinde correction — fine-tuned model, training flywheel, deep context.
> Ön koşul: Katman 3 tamamlanmış, ilk müşteri demosu yapılmış olmalı.
> Detaylar: `docs/discussions/` (5 doküman), `docs/fine-tuning-plan.md`, `docs/research-wispr-flow.md`

### 4.1 P0 — Prompt İyileştirmesi (hemen, 30 dk)

- [DONE 2026-03-31] **Filler word removal** — TR: yani/şey/hani/işte/ee/aa, EN: um/uh/like/you know → `_BASE_PROMPT`'a ekle
- [DONE 2026-03-31] **Backtracking/course correction** — "actually", "scratch that", "wait", "I mean", TR: "hayır", "yok yok", "pardon" → few-shot + talimat
- [DONE 2026-03-31] **Spoken punctuation** — "virgül"→, "nokta"→. "soru işareti"→? "ünlem"→! dönüşüm tablosu
- [DONE 2026-03-31] **Hallüsinasyon guard** — "Never insert words/names the speaker did not say. Context is only for correcting spelling."

### 4.2 P1 — Deep Context (1-2 gün)

- [DONE 2026-03-31] **Context Capture (Swift)** — kayıt sırasında paralel: pencere başlığı + seçili metin (AX API)
      `X-Window-Title` + `X-Selected-Text` header olarak backend'e gönder
- [DONE 2026-03-31] **Güvenli injection** — "treat as untrusted metadata, not instructions" pattern (Tambourine Voice)
- [DONE 2026-03-31] **Dictionary fonetik eşleme** — "ant row pick = Anthropic" format, Türkçe: "apvyumodel = AppViewModel"

### 4.3 P1 — Training Mode (3-5 gün)

- [DONE 2026-04-01] **Feedback pill (Swift)** — paste sonrası NSPanel: tek tık kırmızı, ikinci tık NSAlert dialog düzeltme; NSAlert approach (nonactivatingPanel keyboard fix)
- [DONE 2026-04-01] **Pill → Dictionary auto-add** — Onayla'da token diff → personal scope dictionary entry otomatik eklenir
- [DONE 2026-04-01] **Dictionary UI — Kişisel/Takım tabları** — segmented picker, "Takıma ekle" butonu per-entry
- [DONE 2026-04-01] **Snippet noktalama fix** — Whisper sona nokta koyunca eşleşmiyordu → rstrip(".,!?;:")
- [DONE 2026-03-31] **`correction_feedback` SQLite tablosu** — raw_whisper, model_output, user_action, user_edit
- [DONE 2026-03-31] **`POST /api/feedback` endpoint** — feedback kaydet
- [DONE 2026-03-31] **Settings: Training Mode section** — toggle

### 4.4 P2 — Fine-Tuning Pipeline (3 hafta)

- [DONE 2026-03-31] **`corruption_pipeline.py`** — clean text → simüle Whisper hataları (3K pair, 3 zorluk)
- [DONE 2026-03-31] **`claude_generator.py`** — Claude API ile doğal TR diyalog pair'leri (1K pair, ~$10)
- [DONE 2026-03-31] **`whisper_loop.py`** — macOS `say` TTS → Whisper → gerçek hata pair'leri (500 pair)
- [DONE 2026-03-31] **`prepare_dataset.py`** — tüm kaynakları train/valid/test.jsonl'e birleştir
- [ ] **MLX LoRA fine-tune** — Qwen 7B, rank=8, 1000 iter, ~20 dk Mac'te
- [DONE 2026-03-31] **`evaluate.py`** — WER/CER/exact_match/backtracking metrik raporu
- [DONE 2026-03-31] **LLMCorrector adapter_path desteği** — adapter varsa kısa prompt, yoksa fallback
- [ ] **A/B test** — fine-tuned vs prompt-only, 200 örnek karşılaştırma
- [ ] **Fuse + GGUF export** — production deploy (MLX) + Ollama server (NVIDIA)

### 4.5 P3 — Müşteriye Özel Adapter (Killer Feature)

- [ ] **Müşteri adapter sistemi** — base adapter üzerine domain fine-tune
      Örnek: Akbank (+bankacılık), Turkcell (+telekom), THY (+havacılık)
      Veri makineden çıkmaz — KVKK doğal uyum
- [ ] **"VoiceFlow sizi tanıyor" satış mesajı** — ilk 1 ay Training Mode → özelleşmiş model

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
