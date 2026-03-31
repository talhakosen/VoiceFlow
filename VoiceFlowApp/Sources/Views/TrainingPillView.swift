import SwiftUI
import AppKit

// MARK: - TrainingPillView

/// Floating feedback pill shown after paste when Training Mode is enabled.
/// Shows [Correct] and [Edit] buttons with a 5-second auto-dismiss countdown.
struct TrainingPillView: View {
    var viewModel: AppViewModel

    @State private var editMode = false
    @State private var editText = ""
    @State private var progress: Double = 1.0
    @State private var countdownTask: Task<Void, Never>? = nil

    var body: some View {
        VStack(spacing: 0) {
            if editMode {
                editPanel
            } else {
                pillPanel
            }
        }
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .shadow(color: .black.opacity(0.25), radius: 12, x: 0, y: 4)
        .padding(16)
        .onAppear {
            editText = viewModel.trainingPillResult?.text ?? ""
            startCountdown()
        }
        .onDisappear {
            countdownTask?.cancel()
        }
    }

    // MARK: - Pill (normal state)

    private var pillPanel: some View {
        VStack(spacing: 10) {
            HStack(spacing: 8) {
                Image(systemName: "checkmark.circle")
                    .foregroundStyle(.secondary)
                Text("Was this transcription correct?")
                    .font(.system(size: 13, weight: .medium))
                    .foregroundStyle(.primary)
                Spacer()
            }
            .padding(.horizontal, 14)
            .padding(.top, 12)

            // Progress bar (5s countdown)
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    RoundedRectangle(cornerRadius: 2)
                        .fill(Color.secondary.opacity(0.2))
                        .frame(height: 3)
                    RoundedRectangle(cornerRadius: 2)
                        .fill(Color.accentColor.opacity(0.6))
                        .frame(width: geo.size.width * progress, height: 3)
                        .animation(.linear(duration: 0.1), value: progress)
                }
            }
            .frame(height: 3)
            .padding(.horizontal, 14)

            HStack(spacing: 10) {
                Button {
                    countdownTask?.cancel()
                    Task { await viewModel.approveFeedback() }
                } label: {
                    Label("Correct", systemImage: "checkmark")
                        .font(.system(size: 13, weight: .semibold))
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .tint(.green)

                Button {
                    countdownTask?.cancel()
                    editMode = true
                } label: {
                    Label("Edit", systemImage: "pencil")
                        .font(.system(size: 13, weight: .semibold))
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .tint(.orange)

                Button {
                    countdownTask?.cancel()
                    viewModel.dismissFeedback()
                } label: {
                    Image(systemName: "xmark")
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, 14)
            .padding(.bottom, 12)
        }
        .frame(width: 380)
    }

    // MARK: - Edit panel

    private var editPanel: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Image(systemName: "pencil.circle")
                    .foregroundStyle(.orange)
                Text("Edit transcription")
                    .font(.system(size: 13, weight: .medium))
                Spacer()
                Button {
                    editMode = false
                    startCountdown()
                } label: {
                    Image(systemName: "arrow.uturn.backward")
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
            }

            TextEditor(text: $editText)
                .font(.system(size: 13))
                .frame(height: 80)
                .scrollContentBackground(.hidden)
                .background(Color.secondary.opacity(0.08))
                .clipShape(RoundedRectangle(cornerRadius: 8))

            HStack {
                Spacer()
                Button("Cancel") {
                    editMode = false
                    startCountdown()
                }
                .buttonStyle(.bordered)

                Button("Confirm") {
                    let corrected = editText.trimmingCharacters(in: .whitespacesAndNewlines)
                    guard !corrected.isEmpty else { return }
                    Task { await viewModel.editFeedback(corrected: corrected) }
                }
                .buttonStyle(.borderedProminent)
                .disabled(editText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            }
        }
        .padding(14)
        .frame(width: 380)
    }

    // MARK: - Countdown

    private func startCountdown() {
        progress = 1.0
        countdownTask?.cancel()
        countdownTask = Task {
            let interval = 0.1
            let steps = Int(5.0 / interval)
            for i in 0..<steps {
                try? await Task.sleep(nanoseconds: UInt64(interval * 1_000_000_000))
                if Task.isCancelled { return }
                await MainActor.run {
                    progress = 1.0 - Double(i + 1) / Double(steps)
                }
            }
            if !Task.isCancelled {
                await viewModel.approveFeedback()
            }
        }
    }
}

// MARK: - TrainingPillWindowController

/// NSPanel floating window that hosts TrainingPillView.
/// Auto-closes when showTrainingPill becomes false.
/// Note: must only be called from main thread (NSApplicationDelegate guarantees this).
final class TrainingPillWindowController: NSObject {
    private var panel: NSPanel?
    private var hostingView: NSHostingView<TrainingPillView>?

    func show(viewModel: AppViewModel) {
        guard panel == nil else { return }

        let pillView = TrainingPillView(viewModel: viewModel)
        let hosting = NSHostingView(rootView: pillView)
        hosting.sizingOptions = [.preferredContentSize]
        hostingView = hosting

        let p = NSPanel(
            contentRect: NSRect(x: 0, y: 0, width: 412, height: 120),
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

        // Position bottom-right of screen
        if let screen = NSScreen.main {
            let sw = screen.visibleFrame
            let pw = p.frame.width
            let ph = p.frame.height
            p.setFrameOrigin(NSPoint(
                x: sw.maxX - pw - 24,
                y: sw.minY + 24
            ))
        }

        p.orderFront(nil)
        panel = p
    }

    func close() {
        panel?.orderOut(nil)
        panel = nil
        hostingView = nil
    }
}
