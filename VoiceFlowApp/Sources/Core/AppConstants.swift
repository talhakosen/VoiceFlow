import Foundation

// MARK: - AppConstants
// Uygulama genelinde kullanılan tüm magic number ve sabit değerler.
// Değiştirmek için yalnızca bu dosyayı düzenle.

enum AppConstants {

    // MARK: Network
    static let defaultLocalPort:    Int    = 8765
    static let defaultLocalURL:     String = "http://127.0.0.1:\(defaultLocalPort)"
    static let defaultLocalAPIURL:  String = "\(defaultLocalURL)/api"
    static let alibabaDashScopeURL: String = "https://dashscope-intl.aliyuncs.com/compatible-mode"
    static let alibabaScopeModel:   String = "qwen-max"

    // MARK: Timeouts (seconds)
    static let requestTimeout:     TimeInterval = 30
    static let resourceTimeout:    TimeInterval = 60
    static let healthCheckTimeout: TimeInterval = 3

    // MARK: Polling intervals (nanoseconds)
    static let statePollingInterval:   UInt64 = 100_000_000   // 100ms — AppDelegate store polling
    static let contextIndexingPoll:    UInt64 = 2_000_000_000 // 2s — SettingsFeature context check
    static let menuBarSyncInterval:    Double = 0.3            // MenuBarController UI sync

    // MARK: Hotkey timing (seconds)
    static let doubleTapThreshold:   TimeInterval = 0.4
    static let hotkeyCooldown:        TimeInterval = 0.8
    // Grace period after double-tap start: Fn release within this window is ignored.
    // 3s means normal double-tap + natural hold won't accidentally stop recording.
    // Only an intentional long press (3s+) acts as push-to-talk fallback.
    static let recordingGracePeriod:  TimeInterval = 3.0

    // MARK: History
    static let historyFetchLimit: Int = 50  // HistoryFeature + BackendService default

    // MARK: Training Pill
    static let pillCountdownSeconds: Int = 10

    // MARK: Log paths
    static let swiftLogPath:   String = "/tmp/voiceflow-swift.log"
    static let hotkeyLogPath:  String = "/tmp/voiceflow-hotkey.log"
    static let backendLogPath: String = "/tmp/voiceflow.log"

    // MARK: Sound effects
    static let soundStart: String = "Tink"
    static let soundStop:  String = "Pop"
}
