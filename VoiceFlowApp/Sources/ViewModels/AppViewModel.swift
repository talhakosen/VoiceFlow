import AppKit
import Observation

/// Central app state and business logic.
/// MenuBarController observes this; views bind to it via @Environment.
@Observable
@MainActor
final class AppViewModel {

    // MARK: - State (observed by MenuBarController & Views)

    var isRecording = false
    var statusText = "Ready"
    var lastResult: TranscriptionResult?
    var currentLanguageMode: LanguageMode = .turkish
    var currentAppMode: AppMode = .general
    var isCorrectionEnabled = false

    // MARK: - Dependencies

    private let backend: any BackendServiceProtocol
    private let paste: PasteService
    private let hotkey: HotkeyManager

    private var activeApp: NSRunningApplication?
    private var activeAppBundleID: String? = nil

    // MARK: - Init

    init(
        backend: any BackendServiceProtocol = BackendService(),
        paste: PasteService = PasteService(),
        hotkey: HotkeyManager = HotkeyManager()
    ) {
        self.backend = backend
        self.paste = paste
        self.hotkey = hotkey

        restoreSettings()
        setupHotkey()
    }

    // MARK: - Settings persistence

    private func restoreSettings() {
        let savedMode = UserDefaults.standard.string(forKey: AppSettings.appMode) ?? "general"
        currentAppMode = AppMode(rawValue: savedMode) ?? .general

        let savedLang = UserDefaults.standard.string(forKey: AppSettings.defaultLanguage) ?? LanguageMode.turkish.rawValue
        currentLanguageMode = LanguageMode(rawValue: savedLang) ?? .turkish
    }

    // MARK: - Hotkey wiring

    private func setupHotkey() {
        hotkey.onStartRecording = { [weak self] in
            Task { @MainActor [weak self] in self?.startRecording() }
        }
        hotkey.onStopRecording = { [weak self] in
            Task { @MainActor [weak self] in await self?.stopAndTranscribe() }
        }
        hotkey.start()
    }

    // MARK: - Recording

    func startRecording() {
        guard !isRecording else { return }
        isRecording = true
        statusText = "Recording... (Fn×2 to stop)"
        activeApp = NSWorkspace.shared.frontmostApplication
        activeAppBundleID = activeApp?.bundleIdentifier
        NSSound(named: "Tink")?.play()
        onShowRecordingOverlay?()

        Task {
            do {
                try await backend.startRecording()
            } catch {
                NSLog("VoiceFlow: startRecording failed: %@", error.localizedDescription)
                isRecording = false
                statusText = "Ready"
                onHideRecordingOverlay?()
            }
        }
    }

    func stopAndTranscribe() async {
        guard isRecording else {
            // Sync local state with backend
            if let status = try? await backend.getStatus(), status.isRecording {
                try? await backend.forceStop()
                statusText = "Ready"
            }
            return
        }

        isRecording = false
        statusText = isCorrectionEnabled ? "Transcribing + Correcting..." : "Transcribing..."

        let savedApp = activeApp
        let bundleID = activeAppBundleID
        do {
            let result = try await backend.stopRecording(activeAppBundleID: bundleID)
            lastResult = result
            NSSound(named: "Pop")?.play()
            onHideRecordingOverlay?()
            guard !result.text.isEmpty else {
                statusText = "Ready"
                return
            }
            if let app = savedApp {
                app.activate(options: .activateIgnoringOtherApps)
            }
            try? await Task.sleep(nanoseconds: 300_000_000)
            paste.pasteText(result.text)
            statusText = "Ready"
        } catch {
            NSLog("VoiceFlow: stopAndTranscribe failed: %@", error.localizedDescription)
            onHideRecordingOverlay?()
            statusText = "Ready"
        }
    }

    func forceStop() {
        isRecording = false
        hotkey.resetState()
        statusText = "Force stopping..."
        onHideRecordingOverlay?()
        Task {
            try? await backend.forceStop()
            statusText = "Ready"
        }
    }

    // MARK: - Config changes

    func selectLanguageMode(_ mode: LanguageMode) {
        currentLanguageMode = mode
        UserDefaults.standard.set(mode.rawValue, forKey: AppSettings.defaultLanguage)
        Task {
            try? await backend.updateConfig(
                language: mode.language,
                task: mode.task,
                correctionEnabled: nil,
                mode: nil
            )
        }
    }

    func selectAppMode(_ mode: AppMode) {
        currentAppMode = mode
        UserDefaults.standard.set(mode.rawValue, forKey: AppSettings.appMode)
        Task {
            try? await backend.updateConfig(
                language: currentLanguageMode.language,
                task: currentLanguageMode.task,
                correctionEnabled: nil,
                mode: mode.rawValue
            )
        }
    }

    func toggleCorrection() {
        isCorrectionEnabled.toggle()
        Task {
            try? await backend.updateConfig(
                language: currentLanguageMode.language,
                task: currentLanguageMode.task,
                correctionEnabled: isCorrectionEnabled,
                mode: nil
            )
        }
    }

    // MARK: - Dictionary (Katman 1)

    var dictionaryEntries: [DictionaryEntry] = []

    func loadDictionary() {
        Task {
            dictionaryEntries = (try? await backend.getDictionary()) ?? []
        }
    }

    func addDictionaryEntry(trigger: String, replacement: String, scope: String) {
        Task {
            if let entry = try? await backend.addDictionaryEntry(trigger: trigger, replacement: replacement, scope: scope) {
                dictionaryEntries.append(entry)
            }
        }
    }

    func deleteDictionaryEntry(id: Int) {
        Task {
            try? await backend.deleteDictionaryEntry(id: id)
            dictionaryEntries.removeAll { $0.id == id }
        }
    }

    // MARK: - Snippets (Katman 1)

    var snippetEntries: [SnippetEntry] = []

    func loadSnippets() {
        Task {
            snippetEntries = (try? await backend.getSnippets()) ?? []
        }
    }

    func addSnippet(triggerPhrase: String, expansion: String, scope: String) {
        Task {
            if let entry = try? await backend.addSnippet(triggerPhrase: triggerPhrase, expansion: expansion, scope: scope) {
                snippetEntries.append(entry)
            }
        }
    }

    func deleteSnippet(id: Int) {
        Task {
            try? await backend.deleteSnippet(id: id)
            snippetEntries.removeAll { $0.id == id }
        }
    }

    // MARK: - Context Engine (Phase 2)

    var contextChunkCount: Int = 0
    var isIndexing: Bool = false
    var contextIndexingError: String? = nil

    func loadContextStatus() {
        Task {
            if let status = try? await backend.getContextStatus() {
                contextChunkCount = status.count
            }
        }
    }

    func ingestContext(folderPath: String) {
        isIndexing = true
        contextIndexingError = nil
        Task {
            do {
                try await backend.ingestContext(path: folderPath)
                // Poll until chunk count stabilizes (ingestion runs in background on server)
                var previousCount = -1
                for _ in 0..<30 {  // max ~60s
                    try? await Task.sleep(nanoseconds: 2_000_000_000)
                    if let status = try? await backend.getContextStatus() {
                        contextChunkCount = status.count
                        if status.count > 0 && status.count == previousCount {
                            break  // stable — ingestion complete
                        }
                        previousCount = status.count
                    }
                }
            } catch {
                contextIndexingError = error.localizedDescription
            }
            isIndexing = false
        }
    }

    func clearContext() {
        Task {
            try? await backend.clearContext()
            contextChunkCount = 0
        }
    }

    // MARK: - User profile (@Observable-tracked, persisted via didSet)

    var userName: String = UserDefaults.standard.string(forKey: AppSettings.userName) ?? "" {
        didSet { UserDefaults.standard.set(userName, forKey: AppSettings.userName) }
    }

    var userDepartment: String = UserDefaults.standard.string(forKey: AppSettings.userDepartment) ?? "" {
        didSet { UserDefaults.standard.set(userDepartment, forKey: AppSettings.userDepartment) }
    }

    var userID: String = UserDefaults.standard.string(forKey: AppSettings.userID) ?? ""

    // MARK: - Backend management (injected closures — no AppDelegate dependency)

    var onRestartBackend: ((@escaping (Bool) -> Void) -> Void)?
    var onHardReset: ((@escaping (Bool) -> Void) -> Void)?
    var onShowRecordingOverlay: (() -> Void)?
    var onHideRecordingOverlay: (() -> Void)?

    func restartBackend() {
        statusText = "Restarting backend..."
        onRestartBackend? { [weak self] success in
            Task { @MainActor [weak self] in
                guard let self else { return }
                self.statusText = success ? "Ready" : "Backend restart failed"
                if success {
                    try? await self.backend.updateConfig(
                        language: self.currentLanguageMode.language,
                        task: self.currentLanguageMode.task,
                        correctionEnabled: self.isCorrectionEnabled,
                        mode: self.currentAppMode.rawValue
                    )
                }
            }
        }
    }

    func hardReset() {
        statusText = "Hard resetting..."
        onHardReset? { [weak self] success in
            Task { @MainActor [weak self] in
                self?.statusText = success ? "Ready" : "Hard reset failed"
            }
        }
    }

    // MARK: - Auth (Katman 2)

    var isLoggedIn: Bool = false
    var loginError: String? = nil
    var currentUser: AuthUser? = nil

    func checkLoginState() {
        guard KeychainHelper.accessToken != nil else {
            isLoggedIn = false
            return
        }
        Task {
            do {
                let user = try await backend.getMe()
                currentUser = user
                isLoggedIn = true
            } catch {
                logout()
            }
        }
    }

    func login(email: String, password: String) async {
        loginError = nil
        do {
            let tokens = try await backend.login(email: email, password: password)
            KeychainHelper.accessToken  = tokens.accessToken
            KeychainHelper.refreshToken = tokens.refreshToken
            let user = try await backend.getMe()
            currentUser = user
            isLoggedIn  = true
        } catch BackendError.unauthorized {
            loginError = "E-posta veya şifre hatalı."
        } catch {
            loginError = error.localizedDescription
        }
    }

    func logout() {
        KeychainHelper.accessToken  = nil
        KeychainHelper.refreshToken = nil
        isLoggedIn   = false
        currentUser  = nil
    }

    // MARK: - Accessibility

    var hasAccessibility: Bool { AXIsProcessTrusted() }
}
