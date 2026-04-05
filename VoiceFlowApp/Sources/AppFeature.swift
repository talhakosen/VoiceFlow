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

            // Fix 2: Training pill routing — AppFeature decides based on trainingMode flag.
            // RecordingFeature only sets statusText; AppFeature routes to TrainingFeature.
            case let .recording(.transcriptReceived(result)):
                state.menuBar.hasLastResult = true
                // Fix 3: menuBar.isRecording removed — isRecording lives only in RecordingFeature
                if state.recording.trainingModeEnabled && result.snippetUsed != true {
                    return .send(.training(.pillShown(originalText: result.text)))
                }
                return .none

            // When training pill word corrections applied → update dictionary
            case let .training(.wordCorrectionsApplied(original, corrected)):
                return .send(.settings(.addWordCorrections(original: original, corrected: corrected)))

            default:
                return .none
            }
        }
    }
}
