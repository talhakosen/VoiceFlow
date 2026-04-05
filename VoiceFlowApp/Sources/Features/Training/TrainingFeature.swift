import ComposableArchitecture
import Foundation

@Reducer
struct TrainingFeature {
    @ObservableState
    struct State {
        var isVisible: Bool = false
        var countdown: Int = AppConstants.pillCountdownSeconds
        var originalText: String = ""
        var correctedText: String = ""
        var isShowingEditDialog: Bool = false
    }

    enum Action {
        case pillShown(originalText: String)
        case pillDismissed
        case countdownTicked
        case countdownExpired
        case editTapped
        case editDialogResult(DialogClient.EditResult)
        case feedbackApproved
        case wordCorrectionsApplied(original: String, corrected: String)
    }

    @Dependency(\.continuousClock) var clock
    @Dependency(\.dialogClient) var dialog
    @Dependency(\.pasteClient) var paste
    @Dependency(\.soundClient) var sound

    enum CancelID { case countdown }

    var body: some Reducer<State, Action> {
        Reduce { state, action in
            switch action {
            case let .pillShown(text):
                BackendService.debugLog("TrainingFeature: pillShown — text='\(text)' setting isVisible=true")
                state.isVisible = true
                state.countdown = AppConstants.pillCountdownSeconds
                state.originalText = text
                state.correctedText = text
                return .run { send in
                    for await _ in clock.timer(interval: .seconds(1)) {
                        await send(.countdownTicked)
                    }
                }
                .cancellable(id: CancelID.countdown, cancelInFlight: true)

            case .pillDismissed:
                state.isVisible = false
                state.countdown = AppConstants.pillCountdownSeconds
                return .cancel(id: CancelID.countdown)

            case .countdownTicked:
                state.countdown -= 1
                if state.countdown <= 0 {
                    return .send(.countdownExpired)
                }
                return .none

            case .countdownExpired:
                // Paste already done in RecordingFeature — just close the notification pill
                state.isVisible = false
                BackendService.debugLog("TrainingFeature: countdownExpired — pill closed, paste was already done")
                return .cancel(id: CancelID.countdown)

            case .editTapped:
                let currentText = state.originalText
                return .cancel(id: CancelID.countdown).concatenate(with:
                    .run { send in
                        let result = await dialog.showEditDialog(currentText)
                        await send(.editDialogResult(result))
                    }
                )

            case let .editDialogResult(.saved(corrected)):
                state.isVisible = false
                state.correctedText = corrected
                let original = state.originalText
                return .run { [paste, sound] send in
                    await paste.paste(corrected)
                    sound.play("Pop")
                    await send(.wordCorrectionsApplied(original: original, corrected: corrected))
                }

            case .editDialogResult(.cancelled):
                state.isVisible = false
                return .none

            case .feedbackApproved:
                // Paste already done — just close
                state.isVisible = false
                return .cancel(id: CancelID.countdown)

            case .wordCorrectionsApplied:
                // Handled by parent (SettingsFeature.addWordCorrections)
                return .none
            }
        }
    }
}
