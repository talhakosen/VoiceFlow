import AppKit
import SwiftUI

// MARK: - RecordingOverlayWindow
// Floating pill shown at bottom-center of screen while recording.
// Transparent, non-interactive, always-on-top.

final class RecordingOverlayWindow: NSPanel {

    init() {
        super.init(
            contentRect: .zero,
            styleMask: [.borderless, .nonactivatingPanel],
            backing: .buffered,
            defer: false
        )
        isOpaque = false
        backgroundColor = .clear
        ignoresMouseEvents = true
        level = .floating
        collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        hasShadow = false
        contentViewController = NSHostingController(rootView: RecordingPillView())
        reposition()
    }

    func reposition() {
        guard let screen = NSScreen.main else { return }
        let pillWidth: CGFloat = 140
        let pillHeight: CGFloat = 48
        let screenFrame = screen.visibleFrame
        let x = screenFrame.midX - pillWidth / 2
        let y = screenFrame.minY + 60
        setFrame(NSRect(x: x, y: y, width: pillWidth, height: pillHeight), display: false)
    }
}

// MARK: - RecordingPillView

private struct RecordingPillView: View {
    @State private var amplitudes: [CGFloat] = Array(repeating: 0.3, count: 6)
    @State private var timer: Timer?

    var body: some View {
        HStack(spacing: 4) {
            ForEach(0..<6, id: \.self) { i in
                RoundedRectangle(cornerRadius: 2)
                    .fill(Color.white)
                    .frame(width: 4, height: max(8, amplitudes[i] * 32))
                    .animation(.easeInOut(duration: 0.1), value: amplitudes[i])
            }
        }
        .padding(.horizontal, 20)
        .frame(width: 140, height: 48)
        .background(
            RoundedRectangle(cornerRadius: 24)
                .fill(Color.black.opacity(0.85))
        )
        .onAppear { startAnimation() }
        .onDisappear { timer?.invalidate(); timer = nil }
    }

    private func startAnimation() {
        timer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { _ in
            amplitudes = (0..<6).map { _ in CGFloat.random(in: 0.2...1.0) }
        }
    }
}
