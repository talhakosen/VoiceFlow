import Foundation
import Observation

// MARK: - Training session state machine

enum TrainingSessionState {
    case idle
    case selectingDomain
    case loading
    case inProgress
    case recording
    case transcribing
    case reviewing(transcribed: String)
    case complete(samplesCollected: Int, correctionRate: Double)
    case error(String)
}

// MARK: - TrainingViewModel

@Observable
@MainActor
final class TrainingViewModel {

    // MARK: - Public state

    var sessionState: TrainingSessionState = .idle
    var selectedDomain: String = "general"
    var sentences: [TrainingSentence] = []
    var currentIndex: Int = 0
    var correctionCount: Int = 0       // items where user edited transcription
    var submittedCount: Int = 0        // items saved (next or corrected, not skipped)
    var skippedCount: Int = 0
    var errorMessage: String? = nil

    // Per-sentence
    var currentTranscription: String = ""
    var userCorrection: String = ""

    // MARK: - Computed

    var currentSentence: TrainingSentence? {
        guard currentIndex < sentences.count else { return nil }
        return sentences[currentIndex]
    }

    var progress: Double {
        guard !sentences.isEmpty else { return 0 }
        return Double(currentIndex) / Double(sentences.count)
    }

    var progressLabel: String {
        "\(currentIndex)/\(sentences.count)"
    }

    var correctionRate: Double {
        guard submittedCount > 0 else { return 0 }
        return Double(correctionCount) / Double(submittedCount)
    }

    var correctionRateLabel: String {
        let pct = Int(correctionRate * 100)
        return "\(pct)%"
    }

    var sessionComplete: Bool {
        if case .complete = sessionState { return true }
        return false
    }

    var isRecording: Bool {
        if case .recording = sessionState { return true }
        return false
    }

    var isTranscribing: Bool {
        if case .transcribing = sessionState { return true }
        return false
    }

    // MARK: - Dependencies

    private let backend: any BackendServiceProtocol

    init(backend: any BackendServiceProtocol = BackendService()) {
        self.backend = backend
    }

    // MARK: - Session lifecycle

    func startSession() {
        guard selectedDomain.isEmpty == false else { return }
        sessionState = .loading
        errorMessage = nil
        currentIndex = 0
        correctionCount = 0
        submittedCount = 0
        skippedCount = 0
        sentences = []

        Task {
            do {
                let fetched = try await backend.fetchTrainingSentences(domain: selectedDomain)
                if fetched.isEmpty {
                    errorMessage = "No training sentences found for '\(selectedDomain)'. Check backend."
                    sessionState = .error(errorMessage!)
                    return
                }
                sentences = fetched
                sessionState = .inProgress
            } catch {
                errorMessage = "Backend error: \(error.localizedDescription)"
                sessionState = .error(errorMessage!)
            }
        }
    }

    func resetToIdle() {
        sessionState = .idle
        sentences = []
        currentIndex = 0
        correctionCount = 0
        submittedCount = 0
        skippedCount = 0
        currentTranscription = ""
        userCorrection = ""
        errorMessage = nil
    }

    // MARK: - Recording

    func startRecording() {
        guard case .inProgress = sessionState else { return }
        sessionState = .recording
        currentTranscription = ""
        userCorrection = ""
        Task {
            do {
                try await backend.startRecording()
            } catch {
                sessionState = .inProgress
                errorMessage = "Could not start recording: \(error.localizedDescription)"
            }
        }
    }

    func stopRecordingAndTranscribe() {
        guard case .recording = sessionState else { return }
        sessionState = .transcribing
        Task {
            do {
                let result = try await backend.stopRecording(
                    activeAppBundleID: nil,
                    windowTitle: "VoiceFlow Training",
                    selectedText: nil
                )
                let transcribed = result.text.isEmpty ? (result.rawText ?? "") : result.text
                currentTranscription = transcribed
                userCorrection = transcribed
                sessionState = .reviewing(transcribed: transcribed)
            } catch {
                sessionState = .inProgress
                errorMessage = "Transcription failed: \(error.localizedDescription)"
            }
        }
    }

    // MARK: - Sentence navigation

    func submitAndNext() {
        guard let sentence = currentSentence else { return }
        let corrected = userCorrection.trimmingCharacters(in: .whitespacesAndNewlines)
        let transcribed = currentTranscription.trimmingCharacters(in: .whitespacesAndNewlines)
        let wasEdited = !corrected.isEmpty && corrected != transcribed

        if wasEdited { correctionCount += 1 }
        submittedCount += 1

        let sentenceId = sentence.id
        let original = sentence.text
        let domain = sentence.domain
        let finalCorrected = corrected.isEmpty ? transcribed : corrected

        Task {
            try? await backend.submitTrainingFeedback(
                sentenceId: sentenceId,
                originalText: original,
                transcribedText: transcribed,
                correctedText: finalCorrected,
                domain: domain
            )
        }

        advance()
    }

    func skip() {
        skippedCount += 1
        if isRecording || isTranscribing {
            Task { try? await backend.forceStop() }
        }
        advance()
    }

    private func advance() {
        let nextIndex = currentIndex + 1
        currentTranscription = ""
        userCorrection = ""
        if nextIndex >= sentences.count {
            sessionState = .complete(
                samplesCollected: submittedCount,
                correctionRate: correctionRate
            )
        } else {
            currentIndex = nextIndex
            sessionState = .inProgress
        }
    }
}
