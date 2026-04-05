import ComposableArchitecture

@Reducer
struct AppFeature {
    @ObservableState
    struct State {
        var recording = RecordingFeature.State()
        var settings = SettingsFeature.State()
        var menuBar = MenuBarFeature.State()
        var training = TrainingFeature.State()
        var auth = AuthFeature.State()
        var history = HistoryFeature.State()
    }

    enum Action {
        case recording(RecordingFeature.Action)
        case settings(SettingsFeature.Action)
        case menuBar(MenuBarFeature.Action)
        case training(TrainingFeature.Action)
        case auth(AuthFeature.Action)
        case history(HistoryFeature.Action)
    }

    var body: some Reducer<State, Action> {
        Scope(state: \.recording, action: \.recording) { RecordingFeature() }
        Scope(state: \.settings, action: \.settings) { SettingsFeature() }
        Scope(state: \.menuBar, action: \.menuBar) { MenuBarFeature() }
        Scope(state: \.training, action: \.training) { TrainingFeature() }
        Scope(state: \.auth, action: \.auth) { AuthFeature() }
        Scope(state: \.history, action: \.history) { HistoryFeature() }

        // Cross-feature coordination — must come AFTER all Scope declarations
        Reduce { state, action in
            switch action {

            // When transcript received → show training pill if training mode on
            // Also sync menuBar state (merged from two duplicate cases)
            case let .recording(.transcriptReceived(result)):
                state.menuBar.isRecording = false
                state.menuBar.hasLastResult = true
                if state.recording.trainingModeEnabled {
                    return .send(.training(.pillShown(originalText: result.text)))
                }
                return .none

            // When training pill word corrections applied → update dictionary
            case let .training(.wordCorrectionsApplied(original, corrected)):
                return .send(.settings(.addWordCorrections(original: original, corrected: corrected)))

            // Sync recording state to menuBar on start
            case .recording(.startRecording):
                state.menuBar.isRecording = true
                return .none

            // Sync recording state to menuBar on stop/failure
            case .recording(.forceStop), .recording(.recordingFailed):
                state.menuBar.isRecording = false
                return .none

            // Auth → sync user to recording feature
            case let .auth(.loginResponse(.success(user))):
                return .send(.recording(.userLoggedIn(user)))

            case .auth(.logoutTapped):
                return .send(.recording(.userLoggedOut))

            default:
                return .none
            }
        }
    }
}
