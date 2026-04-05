# VoiceFlow — Mac App Mimarisi

## Stack

**Platform:** macOS 14.0+, Apple Silicon
**Framework:** SwiftUI + AppKit
**Pattern:** TCA (The Composable Architecture) — `@Reducer` + `@ObservableState`
**Dağıtım:** Debug build → `/Applications/VoiceFlow.app`
**Versiyon:** 1.0.x (patch + build, PreToolUse hook ile otomatik artar)

---

## Dosya Yapısı

```
VoiceFlowApp/Sources/
├── VoiceFlowApp.swift               # @main, AppDelegate adaptor
├── AppDelegate.swift                # Lifecycle: Store oluştur, backend başlat, UI yönet
├── AppFeature.swift                 # Root @Reducer — tüm feature'ları compose eder
│
├── Core/
│   ├── BackendService.swift         # HTTP API client (actor, BackendServiceProtocol impl)
│   ├── KeychainHelper.swift         # JWT token saklama
│   ├── Models.swift                 # LanguageMode, AppMode, AppearanceMode, AppSettings
│   ├── SafeHostingView.swift        # NSHostingView crash guard
│   ├── VFDesignSystem.swift         # Merkezi tasarım token sistemi
│   └── Dependencies/
│       ├── BackendClient.swift      # TCA Dependency — BackendServiceProtocol wrapper
│       ├── PasteClient.swift        # TCA Dependency — clipboard + CGEvent Cmd+V
│       ├── SoundClient.swift        # TCA Dependency — ses efektleri
│       ├── DialogClient.swift       # TCA Dependency — NSAlert
│       └── AccessibilityClient.swift # TCA Dependency — AX permission check
│
└── Features/
    ├── Auth/
    │   ├── AuthFeature.swift        # @Reducer — login/logout/token state
    │   └── LoginView.swift          # Login NSPanel view
    ├── History/
    │   ├── HistoryFeature.swift     # @Reducer — history load/clear
    │   └── HistoryView.swift        # Transkripsiyon geçmişi
    ├── MenuBar/
    │   ├── MenuBarFeature.swift     # @Reducer — menu state sync
    │   └── MenuBarController.swift  # NSStatusItem + NSMenu (UI only)
    ├── Onboarding/
    │   └── OnboardingView.swift     # İlk açılış sihirbazı (3 adım)
    ├── Recording/
    │   ├── RecordingFeature.swift   # @Reducer — kayıt + transkripsiyon + paste pipeline
    │   ├── HotkeyManager.swift      # Global Fn double-tap + ⌥1/2/3 dinleyici
    │   ├── ModeIndicatorView.swift  # Sağ üst köşe mod kapsülü
    │   ├── PasteService.swift       # CGEvent Cmd+V implementasyonu
    │   ├── RecordingOverlayWindow.swift # Alt orta floating pill
    │   └── SymbolPickerView.swift   # Engineering mode sembol seçim diyaloğu
    ├── Settings/
    │   ├── SettingsFeature.swift    # @Reducer — dictionary/snippets/context/profile state
    │   ├── SettingsView.swift       # 2-panel settings penceresi
    │   ├── ContextView.swift        # Knowledge Base panel
    │   └── Sections/
    │       ├── GeneralSection.swift
    │       ├── RecordingSection.swift
    │       ├── DictionarySection.swift
    │       ├── SnippetsSection.swift
    │       ├── KnowledgeBaseSection.swift
    │       ├── AccountSection.swift
    │       └── AboutSection.swift
    └── Training/
        ├── TrainingFeature.swift    # @Reducer — IT dataset + training pill state
        ├── ITDatasetView.swift      # IT dataset kayıt ekranı
        └── TrainingPillView.swift   # Sağ alt köşe 60px floating feedback butonu
```

---

## TCA Mimarisi

### AppFeature — Root Reducer

`AppFeature.swift` tüm feature reducer'ları compose eder:

```swift
@Reducer
struct AppFeature {
    @ObservableState
    struct State {
        var recording = RecordingFeature.State()
        var settings  = SettingsFeature.State()
        var menuBar   = MenuBarFeature.State()
        var training  = TrainingFeature.State()
        var auth      = AuthFeature.State()
        var history   = HistoryFeature.State()
    }

    var body: some Reducer<State, Action> {
        Scope(state: \.recording, action: \.recording) { RecordingFeature() }
        Scope(state: \.settings,  action: \.settings)  { SettingsFeature() }
        Scope(state: \.menuBar,   action: \.menuBar)   { MenuBarFeature() }
        Scope(state: \.training,  action: \.training)  { TrainingFeature() }
        Scope(state: \.auth,      action: \.auth)      { AuthFeature() }
        Scope(state: \.history,   action: \.history)   { HistoryFeature() }

        // Cross-feature coordination (AFTER all Scope declarations)
        Reduce { state, action in ... }
    }
}
```

**Cross-feature coordination (AppFeature.Reduce):**
- `.recording(.transcriptReceived)` → `menuBar.hasLastResult = true`; training pill göster (trainingMode açıksa)
- `.training(.wordCorrectionsApplied)` → `settings(.addWordCorrections)` — dictionary auto-add
- `.recording(.startRecording)` → `menuBar.isRecording = true`

### RecordingFeature

Ana kayıt pipeline:

```swift
// State
var isRecording: Bool
var isProcessing: Bool
var statusText: String
var lastResult: TranscriptionResult?
var currentAppMode: AppMode
var currentLanguageMode: LanguageMode
var isCorrectionEnabled: Bool
var isLLMReady: Bool
var whisperModelName: String
var trainingModeEnabled: Bool
var appearanceMode: AppearanceMode
var currentUser: AuthUser?   // Katman 2 auth state mirror
```

**Actions:** `startRecording`, `stopRecording`, `forceStop`, `transcriptReceived`,
`selectAppMode`, `selectLanguageMode`, `setCorrectionEnabled`, `pasteLastResult`,
`setTrainingMode`, `setAppearanceMode`, `approveFeedback`, `editFeedback`, `dismissFeedback`

**Dependency injection:** `@Dependency(\.backendClient)`, `@Dependency(\.pasteClient)`,
`@Dependency(\.soundClient)`

`selectAppMode(.engineering)` → `isCorrectionEnabled = false` (LLM correction otomatik kapatılır)

### SettingsFeature

Dictionary, snippets, context (Knowledge Base), kullanıcı profili state'i:

**State:** `dictionary: [DictionaryEntry]`, `snippets: [SnippetEntry]`, `contextStatus`,
`userName`, `userDepartment`, `llmMode`, `llmEndpoint`

**Actions:** `loadDictionary`, `addDictionaryEntry`, `deleteDictionaryEntry`,
`loadSnippets`, `addSnippet`, `deleteSnippet`, `ingestContext`, `clearContext`,
`addWordCorrections` (cross-feature: TrainingFeature → SettingsFeature)

### MenuBarFeature

Menu görünüm state'ini tutar:

**State:** `isRecording: Bool`, `hasLastResult: Bool`, `statusText: String`

**Actions:** `syncFromRecording`, `toggleRecording`, `pasteLastTranscript`

### TrainingFeature

IT dataset kayıt + training pill feedback:

**State:** `pillShown: Bool`, `originalText: String`, `countdownSeconds: Int`

**Actions:** `pillShown(originalText:)`, `approveFeedback`, `editFeedback`, `dismissFeedback`,
`wordCorrectionsApplied(original:corrected:)` — cross-feature trigger

---

## AppDelegate

```swift
class AppDelegate: NSObject, NSApplicationDelegate {
    // Single TCA store — tüm uygulamada paylaşılır
    let store = Store(initialState: AppFeature.State()) { AppFeature() }

    func applicationDidFinishLaunching(_ notification: Notification) {
        ensureUserID()
        // Store state'ini poll ederek overlay/indicator pencerelerini yönet
        storeObservation = Task { @MainActor in
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 100_000_000) // 100ms
                let recState = store.recording
                // isRecording/isProcessing/showPill değişimlerini overlay'e ilet
            }
        }
        menuBarController = MenuBarController(store: store.scope(state: \.menuBar, ...))
    }
}
```

**Sorumluluklar:**
1. `ensureUserID()` — UUID oluştur (ilk açılış)
2. Tek `Store` oluştur, her yere dağıt
3. State polling (100ms) → RecordingOverlayWindow + ModeIndicatorView yönetimi
4. Backend process başlat (local mode)
5. `MenuBarController` oluştur
6. `requestAccessibilityPermission()`
7. `showOnboardingIfNeeded()`

Backend process yönetimi AppDelegate'te kalır — OS process API'dir, iş mantığı değil.

`startBackend()` `llmMode` UserDefaults'a göre env var set eder:
- `"local"` → `LLM_BACKEND=mlx`
- `"cloud"` → `LLM_BACKEND=ollama` + `LLM_ENDPOINT` (RunPod)
- `"alibaba"` → `LLM_BACKEND=ollama` + DashScope endpoint + `ALIBABA_API_KEY`

---

## Core/Dependencies (TCA Dependency System)

Her dependency `DependencyKey` protokolünü implement eder:

| Dependency | Protokol | Gerçek impl | Test impl |
|---|---|---|---|
| `BackendClient` | `BackendServiceProtocol` | `BackendService` (actor) | `MockBackendService` |
| `PasteClient` | — | CGEvent Cmd+V | no-op |
| `SoundClient` | — | NSSound | no-op |
| `DialogClient` | — | NSAlert | auto-confirm |
| `AccessibilityClient` | — | `AXIsProcessTrusted()` | always-true |

Reducer'larda kullanım:
```swift
@Dependency(\.backendClient) var backend
// Effect içinde:
try await backend.startRecording()
```

---

## BackendServiceProtocol

```swift
protocol BackendServiceProtocol: Actor {
    func startRecording() async throws
    func stopRecording(activeAppBundleID: String?, windowTitle: String?, selectedText: String?,
                       cmdIntervals: [(Double, Double)]?, itDatasetIndex: Int?, trainingMode: Bool)
        async throws -> TranscriptionResult
    func forceStop() async throws
    func getStatus() async throws -> StatusResponse
    func updateConfig(language:task:correctionEnabled:mode:) async throws
    func getHistory(limit:) async throws -> [HistoryItem]
    func clearHistory() async throws
    func getContextStatus() async throws -> ContextStatus
    func ingestContext(path:) async throws
    func clearContext() async throws
    func getDictionary() async throws -> [DictionaryEntry]
    func addDictionaryEntry(trigger:replacement:scope:) async throws -> DictionaryEntry
    func deleteDictionaryEntry(id:) async throws
    func getSnippets() async throws -> [SnippetEntry]
    func addSnippet(triggerPhrase:expansion:scope:) async throws -> SnippetEntry
    func deleteSnippet(id:) async throws
    func getITDatasetNext(offset:) async throws -> ITDatasetResponse
    func saveITDatasetPair(index:whisperOutput:) async throws
    func deleteITDatasetPair(wavPath:) async throws
    func saveUserCorrection(wavPath: String, whisperText: String, correctedText: String) async throws
    func deletePendingWav(wavPath: String) async throws
}
```

---

## MenuBarController

`NSStatusItem` + `NSMenu` — sadece UI, sıfır iş mantığı.

```
[VoiceFlow brand header]
──────────────────────────────────
🎤 Kaydı Başlat / Kaydı Durdur   ← toggle
   Son Transkripsiyonu Yapıştır   ← ⌃⌘V, lastResult yoksa disabled
   Kısayol: Fn × 2               ← disabled, bilgi satırı
   Dil ▶                          ← language submenu
   Mod ▶                          ← mode submenu
⚙  Ayarlar…                       ⌘,
〰  Ses Eğitimi…
↺  Servisi Yeniden Başlat
──────────────────────────────────
⏻  VoiceFlow'dan Çık              ⌘Q
```

- TCA `Store<MenuBarFeature.State, MenuBarFeature.Action>`'dan beslenilir
- `NSMenuDelegate.menuWillOpen` → menü açılmadan önce state sync
- İkon tutarlılığı: `isTemplate = true` SF Symbol (multicolor bozulması önlenir)

---

## HotkeyManager

**Fn double-tap:** start/stop toggle. Release eventi güvenilmez → double-tap + Force Stop yedek.

**Cmd-interval tracking:**
- `recordingDidStart()` → `cmdIntervals = []`
- Kayıt süresince `NSEvent.flagsChanged` ile Cmd basma/bırakma zamanları kaydedilir
- `cmdIntervals: [(Double, Double)]` → `/api/stop` isteğine `X-Cmd-Intervals` header

**⌥1/2/3 global mod kısayolları:**
- keyCode 18→Genel, 19→Mühendislik, 20→Ofis
- `NSEvent.addGlobalMonitorForEvents(.keyDown)` — `.option` modifier'da tetiklenir

---

## UI Bileşenleri

### RecordingOverlayWindow
Alt orta floating pill. İki state:
- `isProcessing = false` → waveform animasyonu
- `isProcessing = true` → 3 nokta bounce

### ModeIndicatorView + ModeIndicatorWindowController
Sağ üst köşe kayan kapsül (`ultraThinMaterial` + mod rengi).
- `showPersistent(mode:)` — kayıt boyunca kalır
- `showBriefly(mode:)` — mod değişiminde 2 sn

### TrainingPillView + TrainingPillWindowController
Sağ alt köşe 60×60px float buton. Paste sonrası 10s geri sayım arc.
- Tıkla → NSAlert + NSTextView edit dialog
- **Kaydet** → token diff → dictionary auto-add (aynı kelime sayısı şartıyla her farklı çift)
- **WAV pipeline:** `trainingMode: true` → backend pending WAV → `saveUserCorrection()` veya `deletePendingWav()`

**Tasarım tutarlılığı:** Overlay + mod göstergesi + training pill → aynı `ultraThinMaterial + renk dili`, 20px sağ kenar boşluğu.

### SettingsView
`NavigationSplitView` **kullanmaz** — custom `HStack` layout:
- **Genişletilmiş** (200px): ikon + metin
- **Daraltılmış** (56px): sadece ikonlar, tooltip ile section adı
- `VFLayout.sidebarCollapsedWidth = 56`, `VFLayout.sidebarWidth = 200`

---

## VFDesignSystem

Merkezi tasarım token sistemi — hardcoded değer yok:

```swift
VFColor.*       // renk paleti
VFFont.*        // tipografi
VFSpacing.*     // boşluk ölçüleri
VFRadius.*      // köşe yarıçapları
VFAnimation.*   // geçiş parametreleri
VFIcon.*        // SF Symbol isimleri
VFLayout.*      // sidebar genişlikleri
```

---

## Models.swift

```swift
enum LanguageMode: String, CaseIterable   // auto, turkish, english, translateToEnglish
enum AppMode: String, CaseIterable        // general, engineering, office
enum AppearanceMode: String, CaseIterable // system, light, dark
enum AppSettings { ... }                  // UserDefaults key constants
```

API modelleri `BackendService.swift`'te:
- `TranscriptionResult` — `text`, `rawText`, `corrected`, `snippetUsed`, `language`, `duration`, `processingMs`, `id`, `itWavPath`, `pendingWavPath`, `symbolRefs: [String]?`
- `StatusResponse`, `HistoryItem`, `HealthResponse`, `ContextStatus`
- `DictionaryEntry`, `SnippetEntry`, `ITDatasetResponse`, `ITRecordingItem`
- `HealthResponse` — `status`, `modelLoaded`, `llmLoaded`, `whisperModel: String?`

---

## AppSettings (UserDefaults Keys)

```swift
enum AppSettings {
    static let deploymentMode     // "local" | "server"
    static let serverURL          // "http://127.0.0.1:8765"
    static let apiKey             // X-Api-Key header
    static let appMode            // "general" | "engineering" | "office"
    static let onboardingComplete // Bool
    static let defaultLanguage    // "tr" | "en" | "auto"
    static let userID             // UUID (auto-generated)
    static let userName           // display name (Account bölümü)
    static let userDepartment     // departman (Account bölümü)
    static let llmMode            // "local" | "cloud" | "alibaba"
    static let llmEndpoint        // Cloud Ollama URL
    static let appearanceMode     // "system" | "light" | "dark"
}
```

**Tema yönetimi:** `RecordingFeature.State.appearanceMode` → `didSet` → `NSApp.appearance` + UserDefaults.

---

## Onboarding

```
AppDelegate.showOnboardingIfNeeded()
    ↓ (onboardingComplete == false)
OnboardingView (NSWindow)
    ├── WelcomeStep
    ├── ModeSelectionStep → AppMode + dil (@AppStorage)
    └── AccessibilityStep → AXIsProcessTrustedWithOptions prompt
```

---

## İzin Gereksinimleri

| İzin | Neden | Not |
|---|---|---|
| Accessibility | Global hotkey + CGEvent paste | Her binary değişikliğinde sıfırlanır |
| Microphone | Ses kaydı | Bir kez, kalıcı |

---

## Build & Deploy

```bash
pkill -f "VoiceFlow.app" 2>/dev/null || true
rm -rf ~/Library/Developer/Xcode/DerivedData/VoiceFlowApp-*
xcodebuild -project VoiceFlowApp/VoiceFlowApp.xcodeproj \
           -scheme VoiceFlowApp -configuration Debug clean build
ditto ~/Library/Developer/Xcode/DerivedData/VoiceFlowApp-*/Build/Products/Debug/VoiceFlow.app \
      /Applications/VoiceFlow.app
open /Applications/VoiceFlow.app
```

DerivedData temizlenmezse eski build kullanılır. Her build sonrası Accessibility izni sıfırlanır.

**Build numaralandırma:** `.claude/hooks/build-number-bump.sh` — PreToolUse hook, her `xcodebuild` çağrısında otomatik:
- `CFBundleVersion` (build number) artar
- `CFBundleShortVersionString` patch artar (1.0.0 → 1.0.1 → ...)
- Settings → About'ta `v1.0.x (build)` formatında görünür

---

## Dağıtım Stratejisi

**App Store YOK** — sandbox global hotkey + paste'i engeller.

- **Debug build:** Geliştirici kullanımı (şu an)
- **Phase 5:** Developer ID imzalama + notarization → DMG → şirket web sitesi
- **Enterprise IT:** MDM (Jamf/Mosyle) ile dağıtım, Accessibility izni MDM profili ile otomatik

---

## Mimari Kısıtlar

- `NSEvent.addGlobalMonitorForEvents` sandbox'ta çalışmaz → DMG şart
- AppKit `NSMenu` → SwiftUI `Menu` ile değiştirilemez (global hotkey koordinasyonu)
- `@ObservableState` macOS 14.0+ gerektirir (deployment target: 14.0)
- TCA Store polling 100ms — AppKit runloop + SwiftUI `withObservationTracking` birlikte kullanılamıyor
