import SwiftUI
import AppKit

// MARK: - TrainingPillView
// Floating "Düzelt" button — bottom-right corner, semi-transparent, 10s countdown.

struct TrainingPillView: View {
    var viewModel: AppViewModel

    @State private var countdown = 10
    @State private var countdownTask: Task<Void, Never>?

    private var displayText: String { viewModel.trainingPillResult?.text ?? "" }

    private let accent = Color.blue

    var body: some View {
        Button {
            countdownTask?.cancel()
            showEditDialog()
        } label: {
            ZStack {
                // Background
                Circle().fill(.ultraThinMaterial)
                Circle().fill(accent.opacity(0.18))
                Circle().strokeBorder(accent.opacity(0.45), lineWidth: 1.5)

                // Countdown arc track
                Circle()
                    .stroke(accent.opacity(0.2), lineWidth: 2.5)
                    .padding(6)

                // Countdown arc progress
                Circle()
                    .trim(from: 0, to: CGFloat(countdown) / 10.0)
                    .stroke(accent.opacity(0.7), style: StrokeStyle(lineWidth: 2.5, lineCap: .round))
                    .padding(6)
                    .rotationEffect(.degrees(-90))
                    .animation(.linear(duration: 1), value: countdown)

                VStack(spacing: 2) {
                    Image(systemName: "pencil")
                        .font(.system(size: 14, weight: .semibold))
                        .foregroundStyle(.white)
                    Text("\(countdown)")
                        .font(.system(size: 10, weight: .semibold, design: .rounded))
                        .foregroundStyle(.white.opacity(0.8))
                }
            }
            .frame(width: 60, height: 60)
            .contentShape(Circle())
        }
        .buttonStyle(.plain)
        .shadow(color: accent.opacity(0.35), radius: 16, x: 0, y: 4)
        .shadow(color: .black.opacity(0.25), radius: 8, x: 0, y: 2)
        .padding(20)
        .onAppear { startCountdown() }
        .onDisappear { countdownTask?.cancel() }
    }

    private func startCountdown() {
        countdownTask = Task {
            for remaining in stride(from: 9, through: 0, by: -1) {
                try? await Task.sleep(nanoseconds: 1_000_000_000)
                guard !Task.isCancelled else { return }
                await MainActor.run { countdown = remaining }
            }
            guard !Task.isCancelled else { return }
            viewModel.dismissFeedback()
        }
    }

    // MARK: - Edit dialog (NSAlert)

    private func showEditDialog() {
        let alert = NSAlert()
        alert.messageText = "Metni Düzelt"
        alert.informativeText = "Doğru metni yazın:"
        alert.alertStyle = .informational
        alert.addButton(withTitle: "Kaydet")
        alert.addButton(withTitle: "İptal")

        let scrollView = NSScrollView(frame: NSRect(x: 0, y: 0, width: 420, height: 100))
        scrollView.hasVerticalScroller = true
        scrollView.hasHorizontalScroller = false
        scrollView.autohidesScrollers = true

        let textView = NSTextView(frame: scrollView.bounds)
        textView.string = displayText
        textView.isEditable = true
        textView.isRichText = false
        textView.font = NSFont.systemFont(ofSize: 13)
        textView.autoresizingMask = [.width]
        scrollView.documentView = textView

        alert.accessoryView = scrollView

        DispatchQueue.main.async {
            textView.selectAll(nil)
        }

        let response = alert.runModal()
        guard response == .alertFirstButtonReturn else {
            viewModel.dismissFeedback()
            return
        }

        let original = displayText
        let corrected = textView.string.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !corrected.isEmpty else { return }

        if corrected != original {
            addWordCorrectionsToDictionary(original: original, corrected: corrected)
            Task { await viewModel.editFeedback(corrected: corrected) }
        } else {
            Task { await viewModel.approveFeedback() }
        }
    }

    private func addWordCorrectionsToDictionary(original: String, corrected: String) {
        let origWords = original.components(separatedBy: .whitespaces).filter { !$0.isEmpty }
        let corrWords = corrected.components(separatedBy: .whitespaces).filter { !$0.isEmpty }
        guard origWords.count == corrWords.count else { return }
        for (orig, corr) in zip(origWords, corrWords) where orig != corr {
            viewModel.addDictionaryEntry(trigger: orig.lowercased(), replacement: corr, scope: "personal")
        }
    }
}

// MARK: - TrainingPillWindowController

final class TrainingPillWindowController: NSObject {
    private var panel: NSPanel?

    func show(viewModel: AppViewModel) {
        guard panel == nil else { return }

        let hosting = SafeHostingView(rootView: TrainingPillView(viewModel: viewModel))
        hosting.sizingOptions = [.preferredContentSize]

        let p = NSPanel(
            contentRect: NSRect(x: 0, y: 0, width: 88, height: 88),
            styleMask: [.borderless, .nonactivatingPanel],
            backing: .buffered,
            defer: false
        )
        p.isFloatingPanel = true
        p.level = .floating
        p.backgroundColor = .clear
        p.isOpaque = false
        p.hasShadow = false
        p.contentView = hosting
        p.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]

        if let screen = NSScreen.main {
            let sw = screen.visibleFrame
            p.setFrameOrigin(NSPoint(x: sw.maxX - p.frame.width - 20, y: sw.minY + 20))
        }

        p.orderFront(nil)
        panel = p
    }

    func close() {
        panel?.orderOut(nil)
        panel = nil
    }
}
