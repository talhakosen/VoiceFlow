import ComposableArchitecture
import SwiftUI
import AppKit

// MARK: - TrainingPillView
// Floating "Düzelt" button — bottom-right corner, semi-transparent, 10s countdown.

struct TrainingPillView: View {
    let store: StoreOf<AppFeature>

    @State private var countdown = 10
    @State private var countdownTask: Task<Void, Never>?

    private var displayText: String { store.recording.trainingPillResult?.text ?? "" }

    private var accent: Color { VFColor.primary }

    var body: some View {
        Button {
            countdownTask?.cancel()
            showEditDialog()
        } label: {
            ZStack {
                // Background
                Circle().fill(.ultraThinMaterial)
                Circle().fill(VFColor.fill(accent))
                Circle().strokeBorder(VFColor.border(accent), lineWidth: 1.5)

                // Countdown arc track
                Circle()
                    .stroke(VFColor.track(accent), lineWidth: 2.5)
                    .padding(VFSpacing.sm)

                // Countdown arc progress
                Circle()
                    .trim(from: 0, to: CGFloat(countdown) / 10.0)
                    .stroke(VFColor.arc(accent), style: StrokeStyle(lineWidth: 2.5, lineCap: .round))
                    .padding(VFSpacing.sm)
                    .rotationEffect(.degrees(-90))
                    .animation(VFAnimation.countdown, value: countdown)

                VStack(spacing: VFSpacing.xxs) {
                    Image(systemName: VFIcon.edit)
                        .font(VFFont.trainingIcon)
                        .foregroundStyle(.white)
                    Text("\(countdown)")
                        .font(VFFont.countdown)
                        .foregroundStyle(.white.opacity(0.8))
                }
            }
            .frame(width: VFLayout.trainingPillSize, height: VFLayout.trainingPillSize)
            .contentShape(Circle())
        }
        .buttonStyle(.plain)
        .vfAccentShadow(accent: accent)
        .padding(VFSpacing.xxxl)
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
            store.send(.recording(.dismissFeedback))
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
            store.send(.recording(.dismissFeedback))
            return
        }

        let original = displayText
        let corrected = textView.string.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !corrected.isEmpty else { return }

        if corrected != original {
            store.send(.settings(.addWordCorrections(original: original, corrected: corrected)))
            store.send(.recording(.editFeedback(corrected: corrected)))
        } else {
            store.send(.recording(.approveFeedback))
        }
    }
}

// MARK: - TrainingPillWindowController

final class TrainingPillWindowController: NSObject {
    private var panel: NSPanel?

    func show(store: StoreOf<AppFeature>) {
        guard panel == nil else { return }

        let hosting = SafeHostingView(rootView: TrainingPillView(store: store))
        hosting.sizingOptions = [.preferredContentSize]

        let p = NSPanel(
            contentRect: NSRect(origin: .zero, size: VFLayout.Overlay.trainingPill),
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
            p.setFrameOrigin(NSPoint(
                x: sw.maxX - p.frame.width  - VFLayout.overlayEdgeInset,
                y: sw.minY + VFLayout.overlayEdgeInset
            ))
        }

        p.orderFront(nil)
        panel = p
    }

    func close() {
        panel?.orderOut(nil)
        panel = nil
    }
}
