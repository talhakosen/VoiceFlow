import ComposableArchitecture
import AppKit

@Reducer
struct MenuBarFeature {
    @ObservableState
    struct State {
        // Fix 3: isRecording removed — read from store.recording.isRecording directly
        var currentAppMode: AppMode = .general
        var currentLanguageMode: LanguageMode = .turkish
        var userRole: String = ""
        var hasLastResult: Bool = false
        var accessibilityGranted: Bool = true
    }

    enum Action {
        // Fix 3: toggleRecording/recordingStopped removed — routing handled by RecordingFeature
        case pasteLastTranscript
        case selectMode(AppMode)
        case selectLanguage(LanguageMode)
        case openAdminPanel
        case restartService
        case checkAccessibility
        case accessibilityStatusReceived(Bool)
        case quit
    }

    @Dependency(\.backendClient) var backend
    @Dependency(\.accessibilityClient) var accessibility

    var body: some Reducer<State, Action> {
        Reduce { state, action in
            switch action {
            case .pasteLastTranscript:
                return .none // delegated to RecordingFeature

            case let .selectMode(mode):
                state.currentAppMode = mode
                return .none

            case let .selectLanguage(lang):
                state.currentLanguageMode = lang
                return .none

            case .openAdminPanel:
                return .run { _ in
                    let baseURL = UserDefaults.standard.string(forKey: "serverURL") ?? "http://127.0.0.1:8765"
                    if let url = URL(string: "\(baseURL)/admin") {
                        await MainActor.run { NSWorkspace.shared.open(url) }
                    }
                }

            case .restartService:
                return .run { _ in try? await backend.forceStop() }

            case .checkAccessibility:
                return .run { send in
                    let trusted = accessibility.isProcessTrusted()
                    await send(.accessibilityStatusReceived(trusted))
                }

            case let .accessibilityStatusReceived(granted):
                state.accessibilityGranted = granted
                return .none

            case .quit:
                return .run { _ in
                    await MainActor.run { NSApplication.shared.terminate(nil) }
                }
            }
        }
    }
}
