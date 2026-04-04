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

    // Training Mode (Katman 4)
    var trainingModeEnabled: Bool = UserDefaults.standard.bool(forKey: AppSettings.trainingMode)
    var showTrainingPill = false
    var trainingPillResult: TranscriptionResult? = nil

    // IT Dataset recording
    var itDatasetActive = false
    var itDatasetCurrentIndex = -1
    var itDatasetLastWhisper = ""
    var itDatasetLastWavPath = ""
    var itDatasetProcessing = false        // true while Whisper result pending (blocks new start)
    var itDatasetCurrentModule: String = "it_dataset"  // active training module
    private var isDatasetRecordingActive = false  // Fn+Space path — Fn path'ini izole eder
    private var autoDismissTask: Task<Void, Never>? = nil

    // MARK: - Dependencies

    private let backend: any BackendServiceProtocol
    private let paste: PasteService
    private let hotkey: HotkeyManager

    private var activeApp: NSRunningApplication?
    private var activeAppBundleID: String? = nil
    // AX context captured at recording start (K4-P1)
    private var capturedWindowTitle: String? = nil
    private var capturedSelectedText: String? = nil

    // Backend health tracking — detect restarts and re-sync config
    private var backendWasAvailable = false
    private var healthCheckTask: Task<Void, Never>? = nil
    var isLLMReady = false
    var whisperModelName: String = ""

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
        startHealthCheck()
    }

    // MARK: - Backend health check + auto config sync

    private func startHealthCheck() {
        healthCheckTask = Task { [weak self] in
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 5_000_000_000) // every 5s
                guard let self else { return }
                if let health = try? await self.backend.getHealth() {
                    let available = health.status == "healthy"
                    self.isLLMReady = health.llmLoaded
                    if let modelName = health.whisperModel, !modelName.isEmpty {
                        self.whisperModelName = modelName
                    }
                    if available && !self.backendWasAvailable {
                        // Backend just came (back) online — push current config
                        try? await self.backend.updateConfig(
                            language: self.currentLanguageMode.language,
                            task: self.currentLanguageMode.task,
                            correctionEnabled: self.isCorrectionEnabled,
                            mode: self.currentAppMode.rawValue
                        )
                        NSLog("VoiceFlow: Backend (re)connected — config synced (correction=%@)", self.isCorrectionEnabled ? "ON" : "OFF")
                    }
                    self.backendWasAvailable = available
                } else {
                    self.backendWasAvailable = false
                    self.isLLMReady = false
                }
            }
        }
    }

    // MARK: - Settings persistence

    private func restoreSettings() {
        let savedMode = UserDefaults.standard.string(forKey: AppSettings.appMode) ?? "general"
        currentAppMode = AppMode(rawValue: savedMode) ?? .general

        let savedLang = UserDefaults.standard.string(forKey: AppSettings.defaultLanguage) ?? LanguageMode.turkish.rawValue
        currentLanguageMode = LanguageMode(rawValue: savedLang) ?? .turkish

        // Correction: engineering → always off; others → use persisted value (default false)
        if currentAppMode == .engineering {
            isCorrectionEnabled = false
        } else {
            isCorrectionEnabled = UserDefaults.standard.bool(forKey: AppSettings.correctionEnabled)
        }
    }

    // MARK: - Hotkey wiring

    private func setupHotkey() {
        hotkey.onStartRecording = { [weak self] in
            Task { @MainActor [weak self] in self?.startRecording() }
        }
        hotkey.onStopRecording = { [weak self] in
            Task { @MainActor [weak self] in await self?.stopAndTranscribe() }
        }
        hotkey.onSwitchMode = { [weak self] index in
            Task { @MainActor [weak self] in
                guard let self else { return }
                let modes = AppMode.allCases
                guard index < modes.count else { return }
                self.selectAppMode(modes[index])
            }
        }
        hotkey.start()
    }

    // MARK: - Recording

    // MARK: - AX Context Capture (K4-P1)

    /// Captures the focused window title using Accessibility API.
    /// Returns nil if permission is not granted or attribute is unavailable.
    private func captureWindowTitle() -> String? {
        guard AXIsProcessTrusted() else { return nil }
        let systemElement = AXUIElementCreateSystemWide()
        var focusedApp: CFTypeRef?
        guard AXUIElementCopyAttributeValue(systemElement, kAXFocusedApplicationAttribute as CFString, &focusedApp) == .success,
              let appElement = focusedApp else { return nil }
        var focusedWindow: CFTypeRef?
        guard AXUIElementCopyAttributeValue(appElement as! AXUIElement, kAXFocusedWindowAttribute as CFString, &focusedWindow) == .success,
              let windowElement = focusedWindow else { return nil }
        var titleValue: CFTypeRef?
        guard AXUIElementCopyAttributeValue(windowElement as! AXUIElement, kAXTitleAttribute as CFString, &titleValue) == .success,
              let title = titleValue as? String, !title.isEmpty else { return nil }
        return sanitizeContextString(title)
    }

    /// Captures selected text in the focused element using Accessibility API.
    /// Returns nil if permission is not granted or no text is selected.
    private func captureSelectedText() -> String? {
        guard AXIsProcessTrusted() else { return nil }
        let systemElement = AXUIElementCreateSystemWide()
        var focusedElement: CFTypeRef?
        guard AXUIElementCopyAttributeValue(systemElement, kAXFocusedUIElementAttribute as CFString, &focusedElement) == .success,
              let element = focusedElement else { return nil }
        var selectedValue: CFTypeRef?
        guard AXUIElementCopyAttributeValue(element as! AXUIElement, kAXSelectedTextAttribute as CFString, &selectedValue) == .success,
              let selected = selectedValue as? String, !selected.isEmpty else { return nil }
        return sanitizeContextString(selected)
    }

    /// Sanitizes context strings: trims, collapses newlines to spaces, strips control chars, truncates to 300 chars.
    private func sanitizeContextString(_ input: String) -> String? {
        let cleaned = input
            .unicodeScalars
            .filter { $0.value >= 0x20 || $0.value == 0x09 }  // keep tab, strip control chars
            .map { Character($0) }
            .reduce("") { $0 + String($1) }
            .components(separatedBy: .newlines)
            .joined(separator: " ")
            .trimmingCharacters(in: .whitespaces)
        guard !cleaned.isEmpty else { return nil }
        return String(cleaned.prefix(300))
    }

    func startRecording() {
        guard !isRecording && !isDatasetRecordingActive else { return }
        isRecording = true
        if isCorrectionEnabled && !isLLMReady {
            statusText = "⚠ LLM yükleniyor — düzeltme bu kayıtta çalışmayabilir"
        } else {
            statusText = "Recording... (Fn×2 to stop)"
        }
        activeApp = NSWorkspace.shared.frontmostApplication
        activeAppBundleID = activeApp?.bundleIdentifier
        // Capture context at recording start (best moment: user has focus on the target app)
        capturedWindowTitle = captureWindowTitle()
        capturedSelectedText = captureSelectedText()
        hotkey.recordingDidStart()
        NSSound(named: "Tink")?.play()
        onShowRecordingOverlay?()

        Task {
            do {
                try await backend.startRecording()
            } catch {
                NSLog("VoiceFlow: startRecording failed: %@", error.localizedDescription)
                isRecording = false
                statusText = "⚠ Servis başlatılıyor..."
                onHideRecordingOverlay?()
            }
        }
    }

    func stopAndTranscribe() async {
        guard !isDatasetRecordingActive else { return }  // Fn+Space kaydını Fn kesmemeli
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
        NSSound(named: "Pop")?.play()
        onShowProcessingOverlay?()

        let savedApp = activeApp
        let bundleID = activeAppBundleID
        let windowTitle = capturedWindowTitle
        let selectedText = capturedSelectedText
        // Reset captured context so it doesn't leak to the next recording
        capturedWindowTitle = nil
        capturedSelectedText = nil
        hotkey.recordingDidStop()
        let cmdIntervals = hotkey.cmdIntervals
        do {
            let result = try await backend.stopRecording(
                activeAppBundleID: bundleID,
                windowTitle: windowTitle,
                selectedText: selectedText,
                cmdIntervals: cmdIntervals.isEmpty ? nil : cmdIntervals,
                itDatasetIndex: nil,
                trainingMode: trainingModeEnabled
            )
            lastResult = result
            guard !result.text.isEmpty else {
                onHideRecordingOverlay?()
                statusText = "Ready"
                return
            }
            if let app = savedApp {
                app.activate(options: .activateIgnoringOtherApps)
            }
            try? await Task.sleep(nanoseconds: 300_000_000)
            paste.pasteText(result.text)
            onHideRecordingOverlay?()

            // Engineering mode: show detected symbols in status
            if let refs = result.symbolRefs, !refs.isEmpty {
                statusText = refs.joined(separator: " · ")
                try? await Task.sleep(nanoseconds: 3_000_000_000)
            }
            statusText = "Ready"

            // Training Mode: show feedback pill after paste — skip if snippet was used
            if trainingModeEnabled && !result.text.isEmpty && result.snippetUsed != true {
                trainingPillResult = result
                showTrainingPill = true
            }
        } catch {
            NSLog("VoiceFlow: stopAndTranscribe failed: %@", error.localizedDescription)
            onHideRecordingOverlay?()
            statusText = "⚠ Bağlantı hatası — servisi yeniden başlatın"
        }
    }

    // MARK: - Training Mode feedback actions (Katman 4)

    func approveFeedback() async {
        guard let result = trainingPillResult else { return }
        autoDismissTask?.cancel()
        autoDismissTask = nil
        showTrainingPill = false
        trainingPillResult = nil
        let rawWhisper = result.rawText ?? result.text
        let modelOutput = result.text
        Task {
            try? await backend.submitFeedback(
                rawWhisper: rawWhisper,
                modelOutput: modelOutput,
                userAction: "approved",
                userEdit: nil
            )
            if let wav = result.pendingWavPath {
                try? await backend.deletePendingWav(wavPath: wav)
            }
        }
    }

    func editFeedback(corrected: String) async {
        guard let result = trainingPillResult else { return }
        autoDismissTask?.cancel()
        autoDismissTask = nil
        showTrainingPill = false
        trainingPillResult = nil
        let rawWhisper = result.rawText ?? result.text
        let modelOutput = result.text
        Task {
            try? await backend.submitFeedback(
                rawWhisper: rawWhisper,
                modelOutput: modelOutput,
                userAction: "edited",
                userEdit: corrected
            )
            if let wav = result.pendingWavPath {
                try? await backend.saveUserCorrection(
                    wavPath: wav,
                    whisperText: rawWhisper,
                    correctedText: corrected
                )
            }
        }
    }

    func dismissFeedback() {
        guard let result = trainingPillResult else {
            showTrainingPill = false
            return
        }
        autoDismissTask?.cancel()
        autoDismissTask = nil
        showTrainingPill = false
        trainingPillResult = nil
        let rawWhisper = result.rawText ?? result.text
        let modelOutput = result.text
        Task {
            try? await backend.submitFeedback(
                rawWhisper: rawWhisper,
                modelOutput: modelOutput,
                userAction: "dismissed",
                userEdit: nil
            )
            if let wav = result.pendingWavPath {
                try? await backend.deletePendingWav(wavPath: wav)
            }
        }
    }

    func forceStop() {
        isRecording = false
        isDatasetRecordingActive = false
        itDatasetProcessing = false
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
        // Mode defaults: Engineering → always off; Office → on; General → off
        switch mode {
        case .engineering:
            isCorrectionEnabled = false
        case .office:
            isCorrectionEnabled = true
        case .general:
            isCorrectionEnabled = false
        }
        UserDefaults.standard.set(mode.rawValue, forKey: AppSettings.appMode)
        UserDefaults.standard.set(isCorrectionEnabled, forKey: AppSettings.correctionEnabled)
        onModeChanged?(mode)
        Task {
            try? await backend.updateConfig(
                language: currentLanguageMode.language,
                task: currentLanguageMode.task,
                correctionEnabled: isCorrectionEnabled,
                mode: mode.rawValue
            )
        }
    }

    func toggleCorrection() {
        guard currentAppMode != .engineering else { return }  // Engineering: always off
        isCorrectionEnabled.toggle()
        UserDefaults.standard.set(isCorrectionEnabled, forKey: AppSettings.correctionEnabled)
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

    // IT Dataset
    func getITDatasetNext(offset: Int) async throws -> ITDatasetResponse {
        try await backend.getITDatasetNext(offset: offset, trainingSet: itDatasetCurrentModule)
    }

    func getITDatasetRandom() async throws -> ITDatasetResponse {
        try await backend.getITDatasetRandom(trainingSet: itDatasetCurrentModule)
    }

    func getITDatasetRecorded() async throws -> [ITDatasetResponse] {
        try await backend.getITDatasetRecorded(trainingSet: itDatasetCurrentModule)
    }

    func deleteITDatasetPair(wavPath: String) {
        Task {
            try? await backend.deleteITDatasetPair(wavPath: wavPath)
        }
    }

    func startRecordingForDataset() {
        guard !isRecording && !itDatasetProcessing else { return }
        isRecording = true
        isDatasetRecordingActive = true
        statusText = "Dataset Recording..."
        Task {
            do {
                try await backend.startRecording()
            } catch {
                isRecording = false
                statusText = "Ready"
            }
        }
    }

    func stopRecordingForDataset() {
        guard isRecording && isDatasetRecordingActive else { return }
        isRecording = false
        isDatasetRecordingActive = false
        itDatasetProcessing = true
        statusText = "Processing..."
        Task {
            do {
                let result = try await backend.stopRecording(
                    activeAppBundleID: nil,
                    windowTitle: nil,
                    selectedText: nil,
                    cmdIntervals: nil,
                    itDatasetIndex: itDatasetCurrentIndex >= 0 ? itDatasetCurrentIndex : nil,
                    trainingMode: false
                )
                if itDatasetActive && itDatasetCurrentIndex >= 0 {
                    itDatasetLastWhisper = result.rawText ?? result.text
                    itDatasetLastWavPath = result.itWavPath ?? ""
                }
                statusText = "Ready"
            } catch {
                statusText = "Ready"
            }
            itDatasetProcessing = false
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
    var indexedProjects: [IndexedProject] = []
    var isIndexing: Bool = false
    var contextIndexingError: String? = nil

    func loadContextStatus() {
        Task {
            if let status = try? await backend.getContextStatus() {
                contextChunkCount = status.count
            }
            if let projects = try? await backend.getContextProjects() {
                indexedProjects = projects.projects
                contextChunkCount = projects.smartWordCount
            }
        }
    }

    func ingestContext(folderPath: String) {
        isIndexing = true
        contextIndexingError = nil
        Task {
            do {
                try await backend.ingestContext(path: folderPath)
                var previousCount = -1
                for _ in 0..<30 {
                    try? await Task.sleep(nanoseconds: 2_000_000_000)
                    if let projects = try? await backend.getContextProjects() {
                        indexedProjects = projects.projects
                        contextChunkCount = projects.smartWordCount
                        let total = projects.totalSymbols
                        if total > 0 && total == previousCount { break }
                        previousCount = total
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
            indexedProjects = []
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
    var onShowProcessingOverlay: (() -> Void)?
    var onHideRecordingOverlay: (() -> Void)?
    var onModeChanged: ((AppMode) -> Void)?

    func restartBackend() {
        isRecording = false
        isDatasetRecordingActive = false
        itDatasetProcessing = false
        backendWasAvailable = false   // health check'i sıfırla — yeniden bağlantıda config push tekrar çalışsın
        hotkey.resetState()
        onHideRecordingOverlay?()
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
