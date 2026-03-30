# VoiceFlow — Mac Uygulama Mimarisi

## Mevcut App (v0.1, Çalışıyor)

**Platform:** macOS 13.0+, Apple Silicon
**Framework:** SwiftUI + AppKit
**Dağıtım:** Debug build → `/Applications/VoiceFlow.app`

### Dosya Yapısı
```
VoiceFlowApp/Sources/
├── VoiceFlowApp.swift      # @main giriş noktası, AppDelegate adaptor
├── AppDelegate.swift       # Backend process yönetimi
├── MenuBarController.swift # Ana UI + akış koordinasyonu
├── HotkeyManager.swift     # Fn key algılama
├── BackendService.swift    # HTTP API client (actor)
└── PasteService.swift      # Clipboard + CGEvent Cmd+V
```

---

## Bileşen Detayları (Doğrulanmış)

### AppDelegate.swift
- Backend Python process'ini başlatır/durdurur (app açılınca/kapanınca)
- Python path: `.venv/bin/python -m voiceflow.main`
- Port 8765'i kontrol eder, çakışma varsa öldürür
- `/health` endpoint'ini 30 deneme × 0.5s ile bekler
- `hardResetBackend()` ve `restartBackend()` sağlar

### HotkeyManager.swift
- `NSEvent.addGlobalMonitorForEvents()` ile global Fn key dinler
- **Double-tap toggle:** 0.4s threshold içinde iki Fn → kayıt başlar/durur
- **Push-to-talk fallback:** Fn bırakılınca da durdurabilir
- Cooldown: 0.8s (kazara tetikleme önleme)
- **Bilinen sorun:** Fn release eventi macOS'ta bazen kaybolur → double-tap birincil yöntem

### BackendService.swift (actor)
```swift
struct TranscriptionResult: Codable {
    let text: String
    let rawText: String?    // Düzeltme varsa
    let corrected: Bool?
    let language: String?
    let duration: Double?
}
```
- Base URL: `http://127.0.0.1:8765/api` (şu an hardcoded)
- Request timeout: 30s, Resource timeout: 60s
- Async/await ile Swift Concurrency

### MenuBarController.swift
- Status icon: `waveform` (boşta) → `waveform.circle.fill` kırmızı (kayıt)
- Language modları: Auto / Türkçe / English / Any→English
- Smart Correction toggle
- History: son 50 transkripsiyon RAM'de (uygulama kapanınca silinir)
- `HistoryView`: SwiftUI penceresi, copy butonu, LLM/Raw badge

### PasteService.swift
- `CGEvent` ile Cmd+V simüle eder (Accessibility izni gerekli)
- `AXIsProcessTrusted()` ile izin kontrolü
- İzin yoksa sessizce başarısız olur (paste çalışmaz ama hata vermez)

---

## İzin Gereksinimleri (Doğrulanmış)

| İzin | Neden | Sorun |
|---|---|---|
| Accessibility | Global hotkey + CGEvent paste | Her binary değişikliğinde sıfırlanır |
| Microphone | Ses kaydı | Bir kez, kalıcı |

**Kritik:** Yeni build deploy edince kullanıcı System Settings → Privacy → Accessibility'den tekrar izin vermeli.

---

## Build & Deploy (Doğrulanmış Komutlar)

```bash
pkill -f "VoiceFlow.app" 2>/dev/null
rm -rf ~/Library/Developer/Xcode/DerivedData/VoiceFlowApp-*
xcodebuild -project VoiceFlowApp/VoiceFlowApp.xcodeproj \
           -scheme VoiceFlowApp -configuration Debug clean build
rm -rf /Applications/VoiceFlow.app
cp -R ~/Library/Developer/Xcode/DerivedData/VoiceFlowApp-*/Build/Products/Debug/VoiceFlow.app \
      /Applications/
open /Applications/VoiceFlow.app
```

DerivedData temizlenmezse eski build kullanılır.

---

## Hedef App (v1.0, Kurumsal)

### Yeni Özellikler

#### 1. Server URL Konfigürasyonu
```swift
// Settings'te kullanıcı URL girer
// Lokal: http://127.0.0.1:8765
// Kurumsal: https://voiceflow.akbank.internal:8765
@AppStorage("serverURL") var serverURL = "http://127.0.0.1:8765"
@AppStorage("apiKey") var apiKey = ""
```

Bu değişince BackendService otomatik yeni URL'i kullanır. Aynı app hem local hem server modunda çalışır.

#### 2. Deployment Modu
- **Local mode:** Backend process'i uygulama başlatır (şu anki gibi)
- **Server mode:** Backend process başlatılmaz, sadece uzak URL'e bağlanır
- Settings'ten seçilir, `AppDelegate`'e geçilir

#### 3. Onboarding Sihirbazı (İlk Açılış)
```
Ekran 1: Hoş geldin + ne işe yarar
Ekran 2: Local mi, Server mi? (URL + API Key)
Ekran 3: Kullanıcı profili (ad, rol, departman)
Ekran 4: Mod seçimi (Engineering / Office / General)
Ekran 5: Microphone + Accessibility izin kontrol
```

#### 4. Mod Sistemi
```swift
enum AppMode: String, CaseIterable {
    case general      = "Genel"
    case engineering  = "Mühendislik"
    case office       = "Ofis"
}
```
- **Engineering:** Prompt'a kod context'i inject edilir
- **Office:** Alıcı profili + ton seçimi
- **General:** Şu anki gibi, sadece transkripsiyon

#### 5. Settings Panel (SwiftUI)
Şu an menu item'ları var. Gerçek settings penceresi gerekli:
- Server URL + API Key
- Kullanıcı profili
- Mod seçimi
- Dil tercihi
- LLM modeli seçimi (server'da hangi model)

#### 6. Persistent History
```swift
// SwiftData veya SQLite.swift
@Model class TranscriptionEntry {
    var id: UUID
    var text: String
    var rawText: String?
    var language: String
    var mode: String
    var timestamp: Date
    var duration: Double
}
```
Son 50 değil, tarih bazlı arama yapılabilir history.

---

## Dağıtım (Distribution)

### Şu An (Debug Build, Geliştirici Kullanımı)
- Xcode debug build → `/Applications/`
- Code signing yok (developer ID ile imzalanmamış)
- Notarization yok
- Sadece aynı Mac'te çalışır

### Kurumsal Dağıtım İçin Gereken
1. **Apple Developer Program** ($99/yıl) — kurumsal imzalama
2. **Developer ID Signing** — `codesign --deep --sign "Developer ID Application: ..."`
3. **Notarization** — `xcrun notarytool submit` → Apple onayı
4. **DMG Paketi** — `create-dmg` ile sürükle-bırak kurulum
5. **Hardened Runtime** — `com.apple.security.cs.allow-unsigned-executable-memory` (MLX için)

### Enterprise IT Dağıtımı
- MDM (Mobile Device Management) ile dağıtım (Jamf, Mosyle)
- Server URL ve API Key pre-configured `.plist` ile
- Accessibility izni MDM profili ile otomatik (enterprise MDM yapabilir)

---

## Mimari Kısıtlar

- AppKit menu bar app → Mac App Store sandbox kısıtlayıcı → **DMG dağıtımı**
- Mac App Store'da global hotkey + auto-paste çok kısıtlı → sandbox dışı şart
- `NSEvent.addGlobalMonitorForEvents` sandbox'ta çalışmaz
