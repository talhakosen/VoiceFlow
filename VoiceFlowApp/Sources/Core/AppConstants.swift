import Foundation

// MARK: - AppConstants
// Uygulama genelinde kullanılan tüm magic number ve sabit değerler.
// Değiştirmek için yalnızca bu dosyayı düzenle.

enum AppConstants {

    // MARK: Network
    static let defaultLocalPort:    Int    = 8765
    static let defaultLocalURL:     String = "http://127.0.0.1:\(defaultLocalPort)"
    static let defaultLocalAPIURL:  String = "\(defaultLocalURL)/api"

    // MARK: Timeouts (seconds)
    static let requestTimeout:     TimeInterval = 30
    static let resourceTimeout:    TimeInterval = 60
    static let healthCheckTimeout: TimeInterval = 3

    // MARK: Polling intervals (nanoseconds)
    static let statePollingInterval:   UInt64 = 100_000_000   // 100ms — AppDelegate store polling
    static let contextIndexingPoll:    UInt64 = 2_000_000_000 // 2s — SettingsFeature context check
    static let menuBarSyncInterval:    Double = 0.3            // MenuBarController UI sync

    // MARK: Hotkey timing (seconds)
    static let hotkeyCooldown:        TimeInterval = 0.3   // cooldown between Fn DOWN toggles

    // MARK: History
    static let historyFetchLimit: Int = 50  // HistoryFeature + BackendService default

    // MARK: Training Pill
    static let pillCountdownSeconds: Int = 10

    // MARK: Paths
    /// Repo konumu değişebilir (proje taşındı: utils/ → personal/).
    /// Tek bir hardcoded path yerine aday listesi denenir; ilk GEÇERLİ olan kullanılır.
    /// "Geçerli" = içinde `src/voiceflow/main.py` var. Bkz. BackendProcessManager.findBackendPath()
    static let backendPathCandidates: [String] = [
        "\(NSHomeDirectory())/Developer/personal/voiceflow/backend",
        "\(NSHomeDirectory())/Developer/utils/voiceflow/backend",
        "\(NSHomeDirectory())/Developer/voiceflow/backend",
    ]

    /// Kullanıcı/geliştirici override — UserDefaults key.
    /// `defaults write com.voiceflow.app backendPathOverride /path/to/backend`
    static let backendPathOverrideKey: String = "backendPathOverride"

    /// Backend dizinini doğrulayan marker dosya.
    static let backendMarkerFile: String = "src/voiceflow/main.py"

    // MARK: Backend watchdog
    static let backendWatchdogInterval: TimeInterval = 5.0   // sağlık kontrolü periyodu
    static let backendMaxAutoRestarts:  Int          = 3     // arka arkaya otomatik restart limiti
    // Limit dolunca watchdog susmuyor, yavaşlıyor: her N tick'te bir yeniden dener
    // (12 × 5sn = 60sn). Engel kalkarsa sistem kendi kendine toparlar.
    static let backendSlowRetryTicks:   Int          = 12

    // MARK: Log paths
    static let swiftLogPath:   String = "/tmp/voiceflow-swift.log"
    static let hotkeyLogPath:  String = "/tmp/voiceflow-hotkey.log"
    static let backendLogPath: String = "/tmp/voiceflow.log"

    // MARK: Sound effects
    static let soundStart: String = "Tink"
    static let soundStop:  String = "Pop"
}
