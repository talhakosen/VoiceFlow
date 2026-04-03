# VoiceFlow — Development Plan

---

## Şu An Çalışan (v0.3.0 — Production Polish Sprint)

- Fn double-tap hotkey ile ses kaydı
- mlx-whisper ile Türkçe/İngilizce transkripsiyon
- Qwen 7B ile isteğe bağlı Türkçe düzeltme (3 mod: general/engineering/office)
- Auto-paste (Cmd+V)
- SQLite persistent history + tenant izolasyonu
- Kişisel Sözlük (user_dictionary) + Sesli Şablonlar (snippets)
- Smart Dictionary (kod tabanı identifier tarama — class/method isimlerini otomatik user_dictionary'e ekler, Türkçe fonetik varyantlar, scope=smart)
- Symbol Index (class/struct/func → file_path:line_number, fuzzy lookup, inline @dosya:satır enjeksiyonu)
- @-trigger: "at/et/add/edd Symbol" → explicit sembol arama, 2-part kuralı bypass
- Engineering mode → LLM correction otomatik kapalı (backend + Swift sync)
- Whisper hallucination loop guard (_strip_hallucination_loop: unigram/bigram/trigram repeat detect)
- Tech Lexicon 2-katman (UNIVERSAL_SUFFIXES + COMMON_DOMAINS + project lexicon, cartesian product trigger generation)
- ChromaDB kaldırıldı — embedding/RAG yok, sıfır bağımlılık
- Recording overlay floating pill + ses efektleri
- 2-panel Settings (Genel/Kayıt/Sözlük/Şablonlar/Bilgi Tabanı/Hesap/Hakkında) — tam Türkçe
- App icon tüm boyutlar doğru (Xcode warning yok)
- Versiyon 0.3.0
- Backend kapalıyken kullanıcıya Türkçe hata mesajı
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
- [DONE 2026-04-02] Engineering mode → LLM correction otomatik kapalı (routes.py auto-unload + AppViewModel UI sync)

### 3.3 Office Package (Derinleştirme)

- [ ] Alıcı profili sistemi (kişiye göre ton)
- [ ] Mail.app + Outlook entegrasyonu (AppleScript / URL scheme)
- [ ] Toplantı notu formatı (otomatik madde işaretleri, action item çıkarma)

### 3.4 Enterprise Distribution

- [DONE 2026-03-30] Docker: `Dockerfile` + `docker-compose.yml` (FastAPI + Ollama + faster-whisper) — non-root, GPU, env secrets, healthcheck
- [DONE 2026-03-31] RunPod: RTX 4090 deploy, Ollama qwen2.5:7b — Settings'ten Local/Cloud/Alibaba toggle
- [DONE 2026-03-31] Alibaba DashScope (qwen-max) — 3. LLM backend seçeneği, dashscope-intl endpoint, API key .env'den
- [DONE 2026-03-31] Backend restart sonrası correction toggle state otomatik gönderilir (AppViewModel.restartBackend fix)
- [DONE 2026-04-01] **Versiyon 1.0.x** — CFBundleShortVersionString patch + CFBundleVersion build, PreToolUse hook otomatik artırır
- [DONE 2026-04-01] **Processing overlay** — kayıt bitince pill kapanmaz; Whisper/LLM süresince 3 nokta bounce animasyonu; paste sonrası kapanır
- [DONE 2026-04-01] **processing_ms** — Whisper+LLM toplam süre; SQLite'a kaydedilir, API response'da döner
- [DONE 2026-04-01] **Backend config sync** — 5s health check; backend restart sonrası config otomatik push edilir; isLLMReady takibi
- [DONE 2026-04-01] **LLM yükleniyor uyarısı** — kayıt başlarken LLM hazır değilse statusText uyarı gösterir
- [DONE 2026-04-01] **Menü polish** — Toggle Recording kaldırıldı; Force Stop → "Kaydı Durdur"; "Servisi Yeniden Başlat" eklendi; alt kısımda versiyon gösterimi
- [DONE 2026-04-01] **LLM_ADAPTER_PATH fix** — AppDelegate env'e eklendi; .env path dosya yerine dizin'e işaret eder
- [ ] DMG paketleme + notarization (Developer ID Application)
- [ ] Kurulum dokümantasyonu (IT için — 1 sayfa, adım adım)
- [ ] Offline lisanslama (license key doğrulama)
- [ ] SSO/SAML hazırlığı (Katman 2 auth'un üzerine, büyük kurumlar için)

---

## KATMAN 4 — Correction Kalitesi & Fine-Tuning (v0.6+)

> Amaç: Wispr Flow kalitesinde correction — fine-tuned model, training flywheel, deep context.
> Ön koşul: Katman 3 tamamlanmış, ilk müşteri demosu yapılmış olmalı.
> Detaylar: `docs/discussions/` (5 doküman), `docs/ml/fine-tuning-plan.md`, `docs/enterprise/research-wispr-flow.md`

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
- [DONE 2026-04-01] **MLX LoRA fine-tune** — Qwen 7B, rank=8, 1000 iter; batch=1 + grad_checkpoint (Mac 16GB); dataset: 3161 pair (corruption + Opus-generated); adapters/ kaydedildi
- [DONE 2026-04-01] **Dataset genişletme** — word_order_pairs (531 pair) + GECTurk-generation (68.745 pair, tüm split'ler); toplam **71.437 pair** → 57K train / 7K valid / 7K test; lora_config.yaml: num_layers=4, iters=3000
- [DONE 2026-03-31] **`evaluate.py`** — WER/CER/exact_match/backtracking metrik raporu
- [DONE 2026-03-31] **LLMCorrector adapter_path desteği** — adapter varsa kısa prompt, yoksa fallback
- [DONE 2026-04-02] **Genişletilmiş dataset ile RunPod LoRA fine-tune** — unsloth SFTTrainer, Qwen2.5-7B, 14115 step, 7 saat RTX 4090; loss=0.78; adapter indirildi → adapters_runpod/ + MLX'e dönüştürüldü → adapters_mlx/; LLM_ADAPTER_PATH .env'e eklendi; model çalışıyor ("korrektat"→"korrekt", "ham"→"hem")
- [DONE 2026-04-02] **ISSAI Turkish Speech Corpus processing** — 186K wav → faster-whisper large-v3 → 177K raw pair; issai_pairs_clean.jsonl: 164K (output ≤ input*1.5 filtresi); data_gen/issai/ altında organize edildi
- [DONE 2026-04-02] **1. round adapter canlı test** — 3 kriter geçti: noktalama ✅, filler temizleme ✅, Türkçe karakter ✅; ISSAI 2. round riski tespit edildi (ground truth noktalamasız → model noktalama silmeyi öğrenir)
- [ ] **A/B test** — fine-tuned vs prompt-only, 200 örnek karşılaştırma
- [ ] **Evaluation WAV test seti** — 100 cümle, gerçek konuşma, farklı hız/ton; Whisper ham + beklenen çiftleri
- [ ] **Fuse + GGUF export** — production deploy (MLX) + Ollama server (NVIDIA)

### 4.5 P2 — Engineering Whisper: Türkiye IT ASR

> "Kubernetes deploy ettim" → Whisper direkt doğru yazsın. Engineering mode'a özel fine-tuned model.

- [DONE 2026-04-02] **`persona_terms.py`** — 8 IT persona (backend/frontend/flutter/.NET/mobile/devops/junior/ml) × terim listesi + Türkçe telaffuz varyantları; 169 benzersiz terim, 294 varyant
- [DONE 2026-04-02] **`sentence_generator.py`** — Qwen-max (Alibaba DashScope) → persona × senaryo + terim-odaklı → **4.495 cümle** (1.115 persona-based + 3.380 terim-focused); whisper_sentences.jsonl
- [DONE 2026-04-02] **`tts_generator.py`** — OpenAI tts-1-hd (alloy/nova/onyx/shimmer) + Edge TTS fallback → 16kHz mono WAV; TTS kalite testi: Edge=yapay, OpenAI=yabancı aksanlı → gerçek insan kaydına pivot
- [DONE 2026-04-02] **IT Dataset Kayıt UI** — Settings > IT Dataset sekmesi; özel Kayıt butonu (Fn2'den bağımsız); WAV + Whisper pair otomatik kaydedilir; play/stop/sil per varyasyon; Finder'da Aç; aynı cümle için birden fazla varyasyon
- [DONE 2026-04-03] **IT Dataset SQLite migration** — training_sentences + training_recordings tabloları; JSONL → SQLite one-time migration; WAV → ~/.voiceflow/training/it_dataset/; multi-training-set (training_set param); ORDER BY RANDOM() shuffle; "Yeni" (unrecorded) + "Pratik" (recorded) tab ayrımı
- [DONE 2026-04-03] **ml/ reorganization** — backend/scripts/ → ml/ (data_gen/, qwen/, whisper/); ml/qwen/{scripts,datasets,adapters_mlx}/; .gitignore güncellendi; tüm docs güncellendi
#### Katman 1 — voiceflow-whisper-tr (ISSAI base)
- [ ] **RunPod pod oluştur** — H100 veya RTX 4090 (SECURE cloud), ISSAI için ~4 saat
- [ ] **ISSAI WAV indir** — RunPod'da `~21GB`, `/root/issai_wav/` altına
- [ ] **`whisper_issai_finetune.py`** — whisper-small (PoC) veya whisper-large-v3-turbo (prod), LoRA r=16, ISSAI 164K pair, 3 epoch
- [ ] **merge_and_unload()** → `voiceflow-whisper-tr` kaydet → MLX'e dönüştür
> Not: ISSAI ground truth noktalama içermiyor → öğrenme hedefi yalnızca fonetik doğruluk

#### Katman 2 — voiceflow-whisper-it (IT layer)
- [ ] **`audio_augment.py`** — hız (0.9×/1.0×/1.2×/1.5×) + gürültü (SNR 5/10/20dB) → ~24K WAV
- [ ] **`build_whisper_dataset.py`** — 70% ISSAI + 30% IT gerçek kayıt → HF dataset format
- [ ] **`whisper_it_finetune.py`** — voiceflow-whisper-tr üzerine IT kayıtlarıyla LoRA, merge → voiceflow-whisper-it
- [ ] **`convert_whisper_mlx.py`** — HF adapter → MLX format → engineering mode entegrasyon
- [ ] **Başarı kriteri**: IT term WER < %5 (mevcut > %30), genel Türkçe kötüleşme < %2

#### Katman 2 — Türkçe IT Podcast Veri Toplama (ek kaynak)
> Trello: https://trello.com/c/lin8J1i8

**Hedef:** YouTube'daki Türkçe IT içeriklerinden gerçek geliştirici konuşması verisi topla.
IT terimi yoğun içerik seçmek kritik — genel Türkçe bölümler değersiz.

**İçerik önceliği:**
1. DevNot Summit teknik sunumlar (Kubernetes, microservice, cloud)
2. Codefiction teknik bölümler (mimari, AWS, Golang başlıklı olanlar)
3. YouTube: "Kubernetes Türkçe", "Docker tutorial TR", "microservice Türkçe" araması

**Pipeline (test edildi 2026-04-03):**
- [ ] Codefiction/DevNot'a lisans için yaz
- [ ] `yt-dlp URL --extract-audio --write-auto-subs --sub-lang tr` → audio + YouTube caption
- [ ] 30sn chunk'lara böl → (chunk.wav, caption_text) JSONL pair
- [ ] voiceflow-whisper-tr üzerine ekle → voiceflow-whisper-it'e dahil et

> Not: YouTube auto-caption (Google STT) ground truth olarak yeterli — Whisper large-v3 pseudo-label gerekmez.
> Not: yt-dlp + ffmpeg RunPod'da kurulu, pipeline hazır.

#### Katman 3 — Müşteri Adapter (Planlandı)
- [ ] **Müşteri adapter sistemi** — voiceflow-whisper-it üzerine domain LoRA (MERGE EDİLMEZ, on-premise)
> Detay: `docs/discussions/007-engineering-whisper-finetune.md`, `docs/ml/two-adapter-architecture.md`

#### PoC Sonuçları (2026-04-02, whisper-small, 48 kayıt, RTX 4090)
- Baseline WER: 40.0% → Fine-tuned WER: 32.5% → **%18.8 iyileşme, 12 saniyede**
- Mimari doğrulandı: merge_and_unload() → katmanlı LoRA çalışıyor

### 4.6 P2 — Quality Monitor: Self-Improving Pipeline

- [ ] **`hallucination_phrases` DB tablosu** — hardcoded liste yerine dinamik; Whisper DB + hardcoded birleşimini okur
- [ ] **Trailing phrase detector** — son 200 transkripsiyonun sonu analiz; %15+ tekrar → hallucination_phrases'e otomatik ekle
- [ ] **Correction pair aggregator** — `raw_text→text` token diff; 3+ tekrar → `dict_suggestions` kuyruğu
- [ ] **Feedback pattern analyzer** — training pill işaretlemeleri → frekans analizi → dict_suggestions
- [ ] **Settings UI: Öneriler bölümü** — "VoiceFlow öğrendi: X → Y [Ekle] [Yoksay]"
- [ ] **WAV cache + drift detection** (P3) — son 20 WAV geçici sakla, analiz sonrası sil (KVKK)
> Detay: `docs/discussions/006-quality-monitor.md`

### 4.6 P3 — Müşteriye Özel Adapter (Killer Feature)

- [ ] **Müşteri adapter sistemi** — base adapter üzerine domain fine-tune
      Örnek: Akbank (+bankacılık), Turkcell (+telekom), THY (+havacılık)
      Veri makineden çıkmaz — KVKK doğal uyum
- [ ] **"VoiceFlow sizi tanıyor" satış mesajı** — ilk 1 ay Training Mode → özelleşmiş model

---

## Mimari Kararlar

- **Local-first, server optional:** Aynı Mac app her iki modda çalışır
- **Açık kaynak modeller:** Cloud API yok — Whisper, Qwen/Llama self-hosted
- **MLX (Mac) + NVIDIA (server):** İki farklı inference engine, env ile seçilir
- **Smart Dictionary:** ChromaDB kaldırıldı; Bilgi Tabanı = kod tabanı identifier tarama → `user_dictionary` tablosuna fonetik varyantlar
- **Mac App Store değil, DMG:** Sandbox global hotkey + paste'i kısıtlar
- **7B minimum LLM:** 1.5B ve 3B Türkçe'de hallüsinasyon yapıyor (doğrulandı)
- **faster-whisper input:** numpy array değil BytesIO — soundfile ile dönüştür
- **Ollama keep_alive=-1:** Model GPU'da sürekli yüklü, cold start yok

### İki Adapter Mimarisi — Katmanlı Eğitim (ML Katmanı)

```
Ses → [Whisper base → voiceflow-whisper-tr → voiceflow-whisper-it] → [Qwen 7B + Qwen Adapter] → Metin
```

**Whisper — 3 Katmanlı Eğitim:**
```
ISSAI (164K) → merge → voiceflow-whisper-tr
                              ↓
                    IT kayıtları → merge → voiceflow-whisper-it   ← deployment base
                                                  ↓
                                    Müşteri verisi → LoRA (on-premise, merge edilmez)
```

| Adapter | Sorumluluk | Durum |
|---|---|---|
| **Qwen Adapter** (~39MB) | Noktalama, filler temizleme, Türkçe karakter, backtracking | ✅ Canlıda (v1, 71K pair) |
| **voiceflow-whisper-tr** | Genel Türkçe fonetik doğruluk (ISSAI base) | 🔲 RunPod eğitimi bekliyor |
| **voiceflow-whisper-it** | IT terim telaffuzu ("doker"→"Docker") | 🔲 whisper-tr sonrası |
| **Müşteri Adapter** (~30MB) | Domain-specific (on-premise, KVKK uyumlu) | 🔲 İlk kurumsal satış sonrası |

- Engineering mode: voiceflow-whisper-it aktif, Qwen Adapter kapalı
- General/Office: Qwen Adapter aktif (correction toggle ile), Whisper base
- Detay: `docs/ml/two-adapter-architecture.md`

---

## Tamamlanan Fazlar

- [DONE] Phase 0: Demo altyapısı (BACKEND_MODE, faster-whisper, Ollama, API key auth)
- [DONE] Phase 0.5: Architecture refactor (layered backend, MVVM Swift)
- [DONE] Phase 1: Foundation (SQLite, mod sistemi, onboarding, kullanıcı profili, history)
- [DONE 2026-04-02] Phase 2: Smart Dictionary + Symbol Index — ChromaDB kaldırıldı; kod tabanı regex tarama → user_dictionary (scope=smart) + symbol_index (file_path:line_number); 2-pass dict matching; CJK hallucination guard; @dosya:satır enjeksiyonu; Bilgi Tabanı UI proje listesi
- [DONE 2026-04-02] Phase 2.1: Symbol Injection iyileştirmeleri — inline replace (başa ekleme değil); Pass 0 @-trigger (at/et/add/edd + 1-word/2-word compact fuzzy); 2-part module kuralı (Server/Model gibi generic kelimeler inject edilmez, explicit class tanımları inject edilir); Engineering mode → LLM auto-off; Whisper hallucination loop guard; Tech Lexicon 2-katman
