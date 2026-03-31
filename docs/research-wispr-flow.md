# Wispr Flow — Araştırma Sonuçları

> Tarih: 30-31 Mart 2026
> Amaç: Rakip analizi, UI/UX referans, kurumsal konumlama farkı, teknik correction pipeline analizi

---

## 1. Mac Uygulaması — Ekran Analizi

### 1.1 Ana Uygulama Yapısı

Wispr Flow bir menü bar app değil — tam bir Mac penceresi + menü bar ikonundan açılır.

**Sol Sidebar Navigation:**
- Home, Dictionary, Snippets, Style, Notes
- Sol alt: "Try Flow Pro" upgrade CTA + Invite / Get free month / Settings / Help

**Home Ekranı:**
- "Welcome back, [İsim]" — kişisel karşılama
- Haftalık istatistikler: 🔥 streak, kelime sayısı, WPM hızı
- Günlük transkript history listesi (saat + metin)
- Ortada feature banner (rotating): "Tag @files and variables hands free"

### 1.2 İçerik Özellikleri

**Dictionary:**
- "Flow speaks the way you speak."
- Kişisel kelime/jargon/şirket adları öğretimi
- Personal / Shared with team tab'ı
- Örnek: "Café Verona", "Q3 Roadmap", "Wnipr → Wispr", "SF MOMA", "Figma Jam", "by-the-way → btw"

**Snippets:**
- "The stuff you shouldn't have to re-type."
- Sesle söylenen kısayol → tam metin açılır
- Örnek: "personal email → user@example.com", "my calendly link → calendly.com/..."
- Personal / Shared with team tab'ı

**Style:**
- Per-context ton ayarı: Formal / Casual / Very Casual
- Tab'lar: Personal messages, Work messages, Email, Other
- Her ton için before/after önizleme kartı

**Notes:**
- Sesle hızlı not alma
- "For quick thoughts you want to come back to"
- Recents listesi

### 1.3 Bildirimler (Gamification)
- Sağ üst bell ikonu → notification panel
- Milestone bildirimleri: "You crossed 2,000 words!", "2 weeks straight!", "777 words — Flow jackpot!"
- Kullanıcıyı alışkanlık kazandırmaya yönelik

### 1.4 Profil Dropdown (sağ üst avatar)
- Plan durumu (Basic: 2000/2000 words left this week)
- "Get Flow Pro" CTA
- Download for iOS (QR kod)
- Manage account

### 1.5 Recording Widget (Float Overlay)
- Shape: koyu rounded pill/capsule
- İçerik: animasyonlu waveform bars (beyaz, koyu bg)
- Aktif text field üzerinde float eder
- Kayıt sırasında hiçbir text göstermez — sadece waveform
- Son derece minimal: konuşunca kaybolur, metin yapıştırılır

### 1.6 Settings Penceresi (2-panel)

**Sol Nav — SETTINGS:**
- General, System, Vibe coding

**Sol Nav — ACCOUNT:**
- Account, Team, Plans and Billing, Data and Privacy

**General:**
- Keyboard shortcuts: "Hold fn and speak"
- Microphone: Built-in mic (recommended)
- Languages: English · Turkish

**System:**
- Launch app at login ✅
- Show Flow bar at all times ✅
- Show app in dock ✅
- Dictation sound effects ✅
- Mute music while dictating ○

**Vibe Coding:**
- Variable recognition (VS Code, Cursor, Windsurf) ○
- File Tagging in Chat (Cursor & Windsurf) ✅

**Account:**
- First name, Last name, Email, Profile picture
- Sign out / Delete account

**Plans and Billing:**
- Basic (Free) / Pro $12/mo / Enterprise (contact us)

**Data and Privacy:**
- Privacy Mode toggle (zero data retention)
- Context awareness toggle
- Hard refresh all notes (Sync notes)
- Delete history of all activity

---

## 2. Kurumsal Ürün Analizi

### 2.1 Plan Yapısı

| Plan | Fiyat | Hedef |
|---|---|---|
| Basic | Ücretsiz | Bireysel — 2,000 kelime/hafta |
| Pro | $12/kullanıcı/ay (yıllık) | Bireysel + küçük ekipler — unlimited |
| Enterprise | ~$24/kullanıcı/ay (tahmini), satış görüşmesi | 50+ kişilik kurumsal |

### 2.2 Enterprise Özellikleri

**Pro'da da olan:**
- Unlimited kelime
- Command Mode (sesle düzenleme komutları)
- Shared Team Dictionary
- Shared Team Snippets
- Merkezi billing
- HIPAA BAA (isteğe bağlı)
- Privacy Mode / Zero Data Retention

**Sadece Enterprise'da:**
- SOC 2 Type II sertifikası
- ISO 27001 sertifikası
- SSO/SAML (WorkOS — Okta, Azure AD, SAML 2.0)
- SCIM provisioning (otomatik kullanıcı yönetimi)
- Enforced HIPAA org genelinde (zorunlu, geri alınamaz)
- Enforced Zero Data Retention org genelinde
- Advanced usage dashboards
- Dedicated Admin Portal
- MSA & DPA
- Bulk pricing

### 2.3 Güvenlik Sertifikaları
- SOC 2 Type II ✅
- ISO 27001 ✅
- HIPAA BAA ✅
- GDPR: Privacy policy'de var, tam uyum belgesi yok
- Trust Center: https://trust.delve.co/wispr-flow

### 2.4 Kritik Zayıflıklar

**Data Residency:** Belirtilmemiş. Coğrafi seçenek yok. Muhtemelen ABD.

**Cloud-only:** On-premise veya air-gap deployment seçeneği YOK.

**3. Taraf AI:** OpenAI + LLaMA API'leri kullanılıyor — veri 3. tarafa gidiyor.

**Android enterprise:** HIPAA/BAA/ZDR enforcement Android'da yok.

**Türkçe:** 100+ dil desteği var ama generic — Türkçe kurumsal jargon optimizasyonu yok.

---

## 3. VoiceFlow ile Karşılaştırma

| Konu | Wispr Flow | VoiceFlow |
|---|---|---|
| Deployment | %100 cloud | **On-premise / private cloud** |
| Data residency | Seçilemez, ABD (muhtemelen) | **Müşterinin kendi sunucusu** |
| AI modeli | OpenAI + LLaMA API | **Kendi modeliniz (MLX / faster-whisper)** |
| Air-gap | Yok — internet şart | **Mümkün** |
| Türkçe optimizasyon | Generic | **Türkçe kurumsal odak** |
| Veri nereye gidiyor? | Wispr sunucularına | **Hiçbir yere — şirket içi kalır** |
| KVKK / BDDK uyumu | Zor — veri yurt dışına çıkıyor | **Doğal uyum — veri hiç çıkmaz** |
| Fiyat modeli | Per-seat SaaS | **Sunucu + flat lisans** |

---

## 4. Konumlama Farkı (Özet)

**Wispr Flow:** *"Güvenli cloud, Zero Data Retention sözü veriyoruz — güvenin bize."*

**VoiceFlow:** *"Veri sizin sunucunuzdan hiç çıkmaz. Güvenmek zorunda değilsiniz, doğrulayabilirsiniz."*

Türkiye'deki BDDK, KVKK, bankacılık düzenlemeleri için Wispr Flow seçilebilir bir ürün bile değil — ses verisi ABD sunucularına gidiyor. VoiceFlow ise sunucuyu müşterinin data center'ına kurarak bu engeli ortadan kaldırıyor.

**Hedef müşteriler:** Akbank, Türkcell, Garanti BBVA, Yapı Kredi, kamu kurumları, savunma sanayi — veri egemenliği zorunlu olan her büyük kurum.

---

## 5. Tasarım Dili Referansları

Wispr Flow'dan alınabilecekler:
- 2-panel Settings penceresi (sol nav + sağ content)
- Minimal floating recording pill (sadece waveform)
- Gamification / istatistikler (Home ekranı)
- Shared Dictionary / Snippets konsepti (kurumsal için Knowledge Base)
- Style/ton seçimi (bizim Mode'a karşılık)

VoiceFlow için farklılaştırma:
- Kurumsal tonlaşma: güven, güvenlik, hız vurgusu
- Türkçe arayüz seçeneği
- On-premise badge / "Verileriniz bu sunucuda" göstergesi
- Enterprise admin paneli (tenant yönetimi)

---

## 6. Teknik Correction Pipeline Analizi (31 Mart 2026)

> Kaynak: Baseten case study, Wispr teknik blog, FreeFlow açık kaynak klonu kaynak kodu, Tambourine Voice

### 6.1 Wispr Flow — İki Aşamalı Cloud Pipeline

```
[Mikrofon] → [ASR/Speech Recognition] → [Fine-tuned Llama LLM] → [Paste]
                  <200ms                      <250ms (100+ token)
                        ──────── toplam <700ms (p99) ────────
```

**Altyapı:**
- ASR: Baseten üzerinde (muhtemelen Whisper varyantı, özelleştirilmiş)
- LLM: Fine-tuned Llama 3.1 — TensorRT-LLM ile optimize
- Multi-step inference: Baseten Chains framework
- Ek provider'lar: OpenAI, Anthropic, Cerebras (text processing)

**Latency bütçesi (p99):**
- ASR inference: <200ms
- LLM inference: <200ms (100+ token generate)
- Network: <200ms (dünya genelinden)
- **Toplam: <700ms**

### 6.2 Wispr Flow — 7 Correction Katmanı

| # | Özellik | Açıklama |
|---|---------|---------|
| 1 | **Filler Word Removal** | "um, uh, like, you know" otomatik silme |
| 2 | **Backtracking / Course Correction** | "yarın buluşalım, hayır cuma olsun" → "Cuma buluşalım" — verbal self-correction'ı anlama |
| 3 | **Context-Aware Tone** | Aktif uygulamaya göre ton (Mail=formal, Slack=casual, Terminal=teknik) |
| 4 | **Personal Dictionary Auto-Learn** | Kullanıcı düzeltmelerini izle, otomatik sözlüğe ekle. "Auto-add to Dictionary" toggle. |
| 5 | **Intelligent Punctuation** | Konuşma kadansı + cümle yapısından noktalama çıkarma, "period/comma" demek gerekmez |
| 6 | **Snippets** | Trigger phrase → template text (60 char trigger, 4000 char expansion, cross-device sync) |
| 7 | **Context-Conditioned ASR** | Konuşmacı özellikleri + çevre konteksti + bireysel geçmiş ile ASR modeli koşullandırma |

**Sahaj Garg (CTO) teknik blog'undan:**
> "Tek kelimelik bir ses klibini düşünün — kişinin sesini, konuşma konularını ve çevre bağlamını bilmeden ne söylediğini çözmek imkansız."

### 6.3 FreeFlow (Açık Kaynak Klon) — Tam Pipeline

> Kaynak: github.com/zachlatta/freeflow — Swift macOS app

**3 Aşamalı Pipeline:**

```
1. KAYIT BAŞLAR → audioRecorder.startRecording()
                → startContextCapture() [PARALEL — kayıt sırasında context alınır]

2. KAYIT BİTER → audioRecorder.stopRecording() → audio file
              → PARALEL:
                 - transcriptionService.transcribe(file)  [Groq Whisper API]
                 - await contextCaptureTask (zaten çalışıyor)
              
3. POST-PROCESS → postProcessingService.postProcess(
                     transcript: rawTranscript,
                     context: 2-cümle appContext özeti,
                     customVocabulary: [...],
                     customSystemPrompt: ...
                  )
              → paste
```

**Stage 1 — Transcription:**
- Model: `whisper-large-v3` (Groq API)
- Audio: 16kHz mono PCM 16-bit WAV
- Timeout: 20 saniye

**Stage 2 — Deep Context (PARALEL — kayıt sırasında):**

macOS Accessibility API ile toplanan veriler:
- `NSWorkspace.shared.frontmostApplication` → uygulama adı, bundle ID
- `kAXFocusedWindowAttribute` → pencere başlığı
- `kAXSelectedTextAttribute` → seçili metin
- `CGWindowListCreateImage` → ekran görüntüsü (JPEG, max 1024px, <500KB base64)

Context inference LLM prompt'u (verbatim):
```
You are a context synthesis assistant for a speech-to-text pipeline.
Given app/window metadata and an optional screenshot, output exactly 
two sentences that describe what the user is doing right now and the 
likely writing intent in the current window.
Prioritize concrete details only from the context: for email, identify 
recipients, subject or thread cues, and whether the user is replying 
or composing; for terminal/code/text work, identify the active command, 
file, document title, or topic.
If details are missing, state uncertainty instead of inventing facts.
Return only two sentences, no labels, no markdown, no extra commentary.
```

Model: `meta-llama/llama-4-scout-17b-16e-instruct` (vision-capable), temp=0.2

**Stage 3 — Post-Processing Correction:**

System prompt (verbatim):
```
You are a dictation post-processor. You receive raw speech-to-text 
output and return clean text ready to be typed into an application.

Your job:
- Remove filler words (um, uh, you know, like) unless they carry meaning.
- Fix spelling, grammar, and punctuation errors.
- When the transcript already contains a word that is a close misspelling 
  of a name or term from the context or custom vocabulary, correct the 
  spelling. Never insert names or terms from context that the speaker 
  did not say.
- Preserve the speaker's intent, tone, and meaning exactly.

Output rules:
- Return ONLY the cleaned transcript text, nothing else.
- If the transcription is empty, return exactly: EMPTY
- Do not add words, names, or content that are not in the transcription. 
  The context is only for correcting spelling of words already spoken.
- Do not change the meaning of what was said.
```

Vocabulary eklentisi (varsa):
```
The following vocabulary must be treated as high-priority terms while 
rewriting. Use these spellings exactly in the output when relevant:
{comma-separated vocabulary terms}
```

User message:
```
Instructions: Clean up RAW_TRANSCRIPTION and return only the cleaned 
transcript text without surrounding quotes. Return EMPTY if there should 
be no result.

CONTEXT: "{contextSummary}"

RAW_TRANSCRIPTION: "{transcript}"
```

Model: `meta-llama/llama-4-scout-17b-16e-instruct`, temp=0.0

**Kritik tasarım kararları:**
- Context özeti sadece 2 cümle — post-processing LLM'e ham screenshot GÖNDERİLMEZ
- Her iki prompt da kullanıcı tarafından özelleştirilebilir (Settings)
- Post-processing başarısız olursa raw Whisper çıktısı kullanılır
- Clipboard korunur: paste öncesi snapshot, 150ms sonra geri yükleme

### 6.4 VoiceFlow Gap Analizi — Correction Pipeline

| Özellik | Wispr Flow | FreeFlow | VoiceFlow | Gap |
|---------|-----------|----------|-----------|-----|
| ASR | Custom (Baseten) | Groq Whisper | mlx-whisper / faster-whisper | Eşit |
| LLM Correction | Fine-tuned Llama | Llama 4 Scout 17B | Qwen 7B / Ollama | **Fine-tune eksik** |
| Filler removal | Built-in (LLM) | Prompt'ta | **Prompt'ta yok** | **P0** |
| Backtracking | Built-in (fine-tune) | Dolaylı (LLM) | **Yok** | **P0** |
| Context awareness | App + screenshot + selected text | App + window + screenshot + LLM özet | App bundle ID → tone | **P1 — Deep Context eksik** |
| Personal dictionary | Auto-learn from corrections | Custom vocabulary | Manuel ekleme | **P1 — Auto-learn eksik** |
| Snippets | Voice triggers | Yok | Backend'de var | Eşit |
| Few-shot examples | Fine-tune data | 1 örnek (prompt'ta) | 5 Türkçe örnek | **İyi** |
| Output safety | Bilinmiyor | EMPTY sentinel | len check + empty check | Eşit |
| Latency | <700ms (cloud) | <1s (Groq) | ~2-5s (local 7B) | **Local trade-off** |

### 6.5 Önerilen İyileştirmeler (Öncelik Sırasına Göre)

**P0 — Hemen (prompt güncellemesi):**
1. Filler word removal talimatı → `_BASE_PROMPT`'a ekle
2. Backtracking/course correction talimatı → `_BASE_PROMPT`'a ekle
3. Few-shot: backtracking + filler örnekleri ekle

**P1 — Kısa vadeli (yeni feature):**
4. Deep Context: aktif pencere başlığı + seçili metin → Swift'ten backend'e gönder
5. Dictionary auto-learn: paste sonrası kullanıcı düzeltmelerini izle, otomatik ekle
6. Context bilgisini user message'a ekle (FreeFlow formatı)

**P2 — Orta vadeli (mimari):**
7. Fine-tuned correction model (Türkçe veri toplayıp Qwen/Llama fine-tune)
8. Context-conditioned ASR (Whisper fine-tune veya prompt conditioning)
9. Paralel context capture (kayıt sırasında, sonra değil)

### 6.6 Referans Prompt'lar (Alınabilecek)

FreeFlow'un post-processing prompt'u bizim `_BASE_PROMPT`'tan daha iyi noktalar:
- **"Remove filler words (um, uh, you know, like) unless they carry meaning"** — bizde yok
- **"Never insert names or terms from context that the speaker did not say"** — hallüsinasyon guard, bizde yok
- **"The context is only for correcting spelling of words already spoken"** — RAG kontekst kullanım sınırı, bizde yok
- **EMPTY sentinel** — boş input handling, bizde farklı (empty string check)

---

## 7. Kaynaklar

- [Wispr Flow + Baseten Case Study](https://www.baseten.co/resources/customers/wispr-flow/)
- [Technical Challenges Behind Flow (Sahaj Garg)](https://wisprflow.ai/post/technical-challenges)
- [FreeFlow — Open Source Wispr Flow Klonu](https://github.com/zachlatta/freeflow)
- [Tambourine Voice — Open Source Alternative](https://github.com/kstonekuan/tambourine-voice)
- [Wispr Flow Features](https://wisprflow.ai/features)
- [Wispr Flow Snippets Docs](https://docs.wisprflow.ai/articles/5784437944-create-and-use-snippets)
- [Wispr Flow Review — Fritz AI](https://fritz.ai/wispr-flow-review/)
- [Wispr Flow 101 — Substack](https://sidsaladi.substack.com/p/wispr-flow-101-the-complete-guide)
