import ComposableArchitecture
import AppKit

// MARK: - RecordingFeature
//
// TCA Reducer covering the recording pipeline.
// AppViewModel stays unchanged — this is additive (Katman 1 TCA migration step 1).

@Reducer
struct RecordingFeature {

    // MARK: - State

    @ObservableState
    struct State {
        var isRecording: Bool = false
        var isProcessing: Bool = false
        var statusText: String = "Ready"
        var lastResult: TranscriptionResult? = nil
        var currentAppMode: AppMode = .general
        var currentLanguageMode: LanguageMode = .turkish
        var isCorrectionEnabled: Bool = false
        var isLLMReady: Bool = false
        var whisperModelName: String = ""
        var llmAdapterVersion: String = ""
        var appearanceMode: AppearanceMode = .system
        // Fix 2: trainingModeEnabled kept for config persistence; training pill state removed
        var trainingModeEnabled: Bool = false
        /// Sabitlenen mikrofon adı; boş = sistem varsayılanı.
        var inputDeviceName: String = ""
        var availableInputDevices: [AudioInputDevice] = []
    }

    // MARK: - Action

    enum Action {
        // Recording controls
        case startRecording
        case stopRecording
        case forceStop
        case recordingFailed(String)
        case transcriptReceived(TranscriptionResult)

        // Paste
        case pasteLastResult

        // Mode / config
        case selectAppMode(AppMode)
        case selectLanguageMode(LanguageMode)
        case setCorrectionEnabled(Bool)
        case setTrainingMode(Bool)
        case setAppearanceMode(AppearanceMode)

        // Mikrofon girişi
        case setInputDevice(String)
        case loadInputDevices
        case inputDevicesLoaded([AudioInputDevice])

        // Dictionary learning (user-triggered from the menu)
        case learnDictionary
        case learnDictionaryFinished(Int)

        // Backend lifecycle
        case restartBackend
        case hardReset
        case backendRestartFinished(Bool)
        case backendStatusReceived(isLLMReady: Bool, whisperModel: String, adapterVersion: String)

        // Accessibility (delegated to AppDelegate / MenuBarFeature)
        case checkAccessibility
    }

    // MARK: - Dependencies

    @Dependency(\.backendClient) var backend
    @Dependency(\.backendProcessClient) var backendProcess
    @Dependency(\.soundClient) var sound
    @Dependency(\.pasteClient) var paste
    @Dependency(\.userDefaultsClient) var userDefaults

    // MARK: - Reducer body

    var body: some Reducer<State, Action> {
        Reduce { state, action in
            switch action {

            // MARK: Recording controls

            case .startRecording:
                guard !state.isRecording else { return .none }
                state.isRecording = true
                if state.isCorrectionEnabled && !state.isLLMReady {
                    state.statusText = "LLM yukleniyor — duzeltme bu kayitta calismayabilir"
                } else {
                    state.statusText = "Kaydediliyor... (Fn×2 durdurmak icin)"
                }
                let lang = state.currentLanguageMode
                let mode = state.currentAppMode
                let correction = state.isCorrectionEnabled
                return .run { send in
                    do {
                        try await backend.startRecording()
                        await MainActor.run { NSSound(named: AppConstants.soundStart)?.play() }
                    } catch {
                        await send(.recordingFailed(error.localizedDescription))
                    }
                    // Also push the current config so backend is in sync
                    try? await backend.updateConfig(
                        lang.language,
                        lang.task,
                        correction,
                        mode.rawValue
                    )
                }

            case .stopRecording:
                guard state.isRecording else { return .none }
                state.isRecording = false
                state.isProcessing = true
                state.statusText = state.isCorrectionEnabled
                    ? "Yaziya dokme + Duzeltme..."
                    : "Yaziya dokme..."
                // TODO: Replace "" with userID from authClient when Katman 2 auth dependency is added
                let trainingMode = state.trainingModeEnabled
                return .run { send in
                    BackendService.debugLog("RecordingFeature: calling stopRecording...")
                    do {
                        let result = try await backend.stopRecording(
                            nil, nil, nil, nil, nil, trainingMode
                        )
                        BackendService.debugLog("RecordingFeature: got result='\(result.text)'")
                        await MainActor.run { NSSound(named: AppConstants.soundStop)?.play() }
                        await send(.transcriptReceived(result))
                    } catch {
                        BackendService.debugLog("RecordingFeature: stopRecording ERROR: \(error)")
                        await send(.recordingFailed(error.localizedDescription))
                    }
                }

            case .forceStop:
                state.isRecording = false
                state.isProcessing = false
                state.statusText = "Ready"
                return .run { _ in
                    try? await backend.forceStop()
                }

            case .learnDictionary:
                // User-triggered from the menu. Heavy (~10s, loads the LLM), so
                // never on the dictation path — runs only on explicit request.
                state.statusText = "VoiceFlow öğreniyor…"
                return .run { send in
                    let added = (try? await backend.learnDictionary()) ?? 0
                    await send(.learnDictionaryFinished(added))
                }

            case let .learnDictionaryFinished(added):
                state.statusText = added > 0
                    ? "\(added) yeni kelime öğrenildi"
                    : "Yeni bir şey öğrenilmedi"
                return .none

            case let .recordingFailed(msg):
                state.isRecording = false
                state.isProcessing = false
                state.statusText = "Hata: \(msg)"
                return .none

            case let .transcriptReceived(result):
                BackendService.debugLog("transcriptReceived: text='\(result.text)'")
                state.isProcessing = false
                state.lastResult = result
                guard !result.text.isEmpty else {
                    // Backend sessiz dönebilir ama sebebini biliyorsa söylesin —
                    // "kayıt oluyor, panoya bir şey gelmiyor" sessiz hatasını önler.
                    state.statusText = result.notice.map { "Hata: \($0)" } ?? "Ready"
                    return .none
                }
                let trainingMode = state.trainingModeEnabled
                BackendService.debugLog("transcriptReceived: trainingMode=\(trainingMode) — pasting immediately")
                state.statusText = result.text
                return .run { [text = result.text] _ in
                    BackendService.debugLog("transcriptReceived: calling paste with '\(text)'")
                    await paste.paste(text)
                    BackendService.debugLog("transcriptReceived: paste done")
                }

            // MARK: Paste

            case .pasteLastResult:
                guard let result = state.lastResult, !result.text.isEmpty else { return .none }
                return .run { [text = result.text] _ in
                    await paste.paste(text)
                }

            // MARK: Mode / config

            case let .selectAppMode(mode):
                state.currentAppMode = mode
                // Mode defaults: Engineering → always off; Office → on; General → off
                switch mode {
                case .engineering:
                    state.isCorrectionEnabled = false
                case .office:
                    state.isCorrectionEnabled = true
                case .general:
                    state.isCorrectionEnabled = false
                }
                userDefaults.setString(mode.rawValue, AppSettings.appMode)
                userDefaults.setBool(state.isCorrectionEnabled, AppSettings.correctionEnabled)
                let lang = state.currentLanguageMode
                let correction = state.isCorrectionEnabled
                return .run { _ in
                    try? await backend.updateConfig(
                        lang.language,
                        lang.task,
                        correction,
                        mode.rawValue
                    )
                }

            case let .selectLanguageMode(lang):
                state.currentLanguageMode = lang
                userDefaults.setString(lang.rawValue, AppSettings.defaultLanguage)
                let mode = state.currentAppMode
                return .run { _ in
                    try? await backend.updateConfig(
                        lang.language,
                        lang.task,
                        nil,
                        mode.rawValue
                    )
                }

            case let .setCorrectionEnabled(enabled):
                guard state.currentAppMode != .engineering else { return .none }
                state.isCorrectionEnabled = enabled
                userDefaults.setBool(enabled, AppSettings.correctionEnabled)
                let lang = state.currentLanguageMode
                let mode = state.currentAppMode
                return .run { _ in
                    try? await backend.updateConfig(
                        lang.language,
                        lang.task,
                        enabled,
                        mode.rawValue
                    )
                }

            case let .setTrainingMode(enabled):
                state.trainingModeEnabled = enabled
                userDefaults.setBool(enabled, AppSettings.trainingMode)
                return .none

            case let .setAppearanceMode(mode):
                state.appearanceMode = mode
                userDefaults.setString(mode.rawValue, AppSettings.appearanceMode)
                return .run { _ in
                    await MainActor.run { NSApp.appearance = mode.nsAppearance }
                }

            // MARK: Mikrofon girişi

            case let .setInputDevice(name):
                state.inputDeviceName = name
                userDefaults.setString(name, AppSettings.inputDevice)
                return .run { _ in
                    // Backend yeniden başlayınca ayar sıfırlanır — AppDelegate
                    // her sağlıklı başlangıçta bunu tekrar gönderir.
                    try? await backend.setInputDevice(name)
                }

            case .loadInputDevices:
                return .run { send in
                    let devices = (try? await backend.getInputDevices()) ?? []
                    await send(.inputDevicesLoaded(devices))
                }

            case let .inputDevicesLoaded(devices):
                state.availableInputDevices = devices
                return .none

            // MARK: Backend lifecycle

            case .restartBackend:
                state.statusText = "Yeniden baslatiliyor..."
                state.isRecording = false
                state.isProcessing = false
                return .run { send in
                    // Önce nazikçe kaydı bitir (backend ayaktaysa), sonra SÜRECİ yeniden başlat.
                    // Sadece forceStop atmak yetmiyordu: backend ölüyse buton hiçbir şey yapmıyordu.
                    try? await backend.forceStop()
                    await send(.backendStatusReceived(isLLMReady: false, whisperModel: "", adapterVersion: ""))
                    let ok = await backendProcess.restart()
                    await send(.backendRestartFinished(ok))
                }

            case .hardReset:
                state.isRecording = false
                state.isProcessing = false
                state.statusText = "Sifirlaniyor..."
                return .run { send in
                    await send(.backendStatusReceived(isLLMReady: false, whisperModel: "", adapterVersion: ""))
                    let ok = await backendProcess.hardReset()
                    await send(.backendRestartFinished(ok))
                }

            case let .backendRestartFinished(ok):
                state.isRecording = false
                state.isProcessing = false
                state.statusText = ok
                    ? "Servis hazir"
                    : "Hata: " + (backendProcess.lastFailureMessage() ?? "Servis baslatilamadi")
                return .none

            case let .backendStatusReceived(llmReady, whisper, adapter):
                state.isLLMReady = llmReady
                if !whisper.isEmpty { state.whisperModelName = whisper }
                if !adapter.isEmpty { state.llmAdapterVersion = adapter }
                return .none

            // MARK: Accessibility

            case .checkAccessibility:
                // Handled by AppDelegate / MenuBarController
                return .none
            }
        }
    }
}
