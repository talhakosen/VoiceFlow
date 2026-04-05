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
        var trainingModeEnabled: Bool = false
        var showTrainingPill: Bool = false
        var trainingPillResult: TranscriptionResult? = nil
        var appearanceMode: AppearanceMode = .system

        // Auth state — mirrors AppViewModel (Katman 2)
        var currentUser: AuthUser? = nil
        var isLoggedIn: Bool = false
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

        // Training pill feedback
        case approveFeedback
        case editFeedback(corrected: String)
        case dismissFeedback

        // Backend lifecycle
        case restartBackend
        case hardReset
        case backendStatusReceived(isLLMReady: Bool, whisperModel: String, adapterVersion: String)

        // Auth
        case userLoggedIn(AuthUser)
        case userLoggedOut

        // Accessibility (delegated to AppDelegate / MenuBarFeature)
        case checkAccessibility
    }

    // MARK: - Dependencies

    @Dependency(\.backendClient) var backend
    @Dependency(\.soundClient) var sound
    @Dependency(\.pasteClient) var paste

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
                        await MainActor.run { NSSound(named: "Tink")?.play() }
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
                let userID = state.currentUser?.userId ?? ""
                let trainingMode = state.trainingModeEnabled
                return .run { send in
                    do {
                        let result = try await backend.stopRecording(
                            nil,   // activeAppBundleID — captured by AppViewModel for now
                            nil,   // windowTitle
                            nil,   // selectedText
                            nil,   // cmdIntervals
                            nil,   // itDatasetIndex
                            trainingMode
                        )
                        await MainActor.run { NSSound(named: "Pop")?.play() }
                        await send(.transcriptReceived(result))
                    } catch {
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

            case let .recordingFailed(msg):
                state.isRecording = false
                state.isProcessing = false
                state.statusText = "Hata: \(msg)"
                return .none

            case let .transcriptReceived(result):
                state.isProcessing = false
                state.lastResult = result
                guard !result.text.isEmpty else {
                    state.statusText = "Ready"
                    return .none
                }
                if state.trainingModeEnabled && result.snippetUsed != true {
                    state.showTrainingPill = true
                    state.trainingPillResult = result
                    state.statusText = "Duzelt veya onayla"
                    return .none
                } else {
                    state.statusText = result.text
                    return .run { [text = result.text] _ in
                        paste.paste(text)
                    }
                }

            // MARK: Paste

            case .pasteLastResult:
                guard let result = state.lastResult, !result.text.isEmpty else { return .none }
                return .run { [text = result.text] _ in
                    paste.paste(text)
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
                UserDefaults.standard.set(mode.rawValue, forKey: AppSettings.appMode)
                UserDefaults.standard.set(state.isCorrectionEnabled, forKey: AppSettings.correctionEnabled)
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
                UserDefaults.standard.set(lang.rawValue, forKey: AppSettings.defaultLanguage)
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
                UserDefaults.standard.set(enabled, forKey: AppSettings.correctionEnabled)
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
                UserDefaults.standard.set(enabled, forKey: AppSettings.trainingMode)
                return .none

            case let .setAppearanceMode(mode):
                state.appearanceMode = mode
                UserDefaults.standard.set(mode.rawValue, forKey: AppSettings.appearanceMode)
                return .run { _ in
                    await MainActor.run { NSApp.appearance = mode.nsAppearance }
                }

            // MARK: Training pill feedback

            case .approveFeedback:
                guard let result = state.trainingPillResult else { return .none }
                state.showTrainingPill = false
                state.trainingPillResult = nil
                state.statusText = result.text
                let rawWhisper = result.rawText ?? result.text
                let modelOutput = result.text
                let wav = result.pendingWavPath
                return .run { [text = result.text] _ in
                    paste.paste(text)
                    await MainActor.run { NSSound(named: "Pop")?.play() }
                    try? await backend.submitFeedback(rawWhisper, modelOutput, "approved", nil)
                    if let wav {
                        try? await backend.deletePendingWav(wav)
                    }
                }

            case let .editFeedback(corrected):
                guard let result = state.trainingPillResult else { return .none }
                state.showTrainingPill = false
                state.trainingPillResult = nil
                state.statusText = corrected
                let rawWhisper = result.rawText ?? result.text
                let modelOutput = result.text
                let wav = result.pendingWavPath
                return .run { _ in
                    paste.paste(corrected)
                    await MainActor.run { NSSound(named: "Pop")?.play() }
                    try? await backend.submitFeedback(rawWhisper, modelOutput, "edited", corrected)
                    if let wav {
                        try? await backend.saveUserCorrection(wav, rawWhisper, corrected)
                    }
                }

            case .dismissFeedback:
                guard let result = state.trainingPillResult else {
                    state.showTrainingPill = false
                    return .none
                }
                state.showTrainingPill = false
                state.trainingPillResult = nil
                let rawWhisper = result.rawText ?? result.text
                let modelOutput = result.text
                let wav = result.pendingWavPath
                return .run { _ in
                    try? await backend.submitFeedback(rawWhisper, modelOutput, "dismissed", nil)
                    if let wav {
                        try? await backend.deletePendingWav(wav)
                    }
                }

            // MARK: Backend lifecycle

            case .restartBackend:
                state.statusText = "Yeniden baslatiliyor..."
                state.isRecording = false
                state.isProcessing = false
                return .run { send in
                    try? await backend.forceStop()
                    await send(.backendStatusReceived(isLLMReady: false, whisperModel: "", adapterVersion: ""))
                }

            case .hardReset:
                state.isRecording = false
                state.isProcessing = false
                state.statusText = "Sifirlaniyor..."
                return .run { send in
                    try? await backend.forceStop()
                    await send(.backendStatusReceived(isLLMReady: false, whisperModel: "", adapterVersion: ""))
                }

            case let .backendStatusReceived(llmReady, whisper, adapter):
                state.isLLMReady = llmReady
                if !whisper.isEmpty { state.whisperModelName = whisper }
                if !adapter.isEmpty { state.llmAdapterVersion = adapter }
                return .none

            // MARK: Auth

            case let .userLoggedIn(user):
                state.currentUser = user
                state.isLoggedIn = true
                return .none

            case .userLoggedOut:
                state.currentUser = nil
                state.isLoggedIn = false
                return .none

            // MARK: Accessibility

            case .checkAccessibility:
                // Handled by AppDelegate / MenuBarController
                return .none
            }
        }
    }
}
