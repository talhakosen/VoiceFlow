# Wispr Flow — Araştırma Sonuçları

> Tarih: 30 Mart 2026
> Amaç: Rakip analizi, UI/UX referans, kurumsal konumlama farkı

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
