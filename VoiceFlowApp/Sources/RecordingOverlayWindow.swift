import AppKit
import SwiftUI

// MARK: - PillCharacter
// Aktif loading karakterini değiştirmek için buraya bak:
enum PillCharacter {
    case dots   // 3 bounce dots (klasik)
    case face   // düşünen surat (göz kırpma + ağız döngüsü)

    static let active: PillCharacter = .dots
}

// MARK: - PillState

final class PillState: ObservableObject {
    @Published var isProcessing: Bool = false
}

// MARK: - RecordingOverlayWindow
// Floating pill shown at bottom-center of screen while recording or processing.

final class RecordingOverlayWindow: NSPanel {
    let pillState = PillState()

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
        contentViewController = NSHostingController(rootView: RecordingPillView(state: pillState))
        reposition()
    }

    func showRecording() {
        pillState.isProcessing = false
        reposition()
        orderFrontRegardless()
    }

    func showProcessing() {
        pillState.isProcessing = true
        orderFrontRegardless()
    }

    func hide() {
        pillState.isProcessing = false
        orderOut(nil)
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
    @ObservedObject var state: PillState
    @State private var amplitudes: [CGFloat] = Array(repeating: 0.3, count: 6)
    @State private var waveTimer: Timer?

    var body: some View {
        ZStack {
            if state.isProcessing {
                processingView
            } else {
                waveformView
            }
        }
        .frame(width: 140, height: 48)
        .background(
            RoundedRectangle(cornerRadius: 24)
                .fill(Color.black.opacity(0.85))
        )
        .onChange(of: state.isProcessing) { _, processing in
            if processing {
                waveTimer?.invalidate(); waveTimer = nil
            } else {
                startWaveTimer()
            }
        }
        .onAppear { startWaveTimer() }
        .onDisappear { waveTimer?.invalidate(); waveTimer = nil }
    }

    // Waveform bars (recording state)
    private var waveformView: some View {
        HStack(spacing: 4) {
            ForEach(0..<6, id: \.self) { i in
                RoundedRectangle(cornerRadius: 2)
                    .fill(Color.white)
                    .frame(width: 4, height: max(8, amplitudes[i] * 32))
                    .animation(.easeInOut(duration: 0.1), value: amplitudes[i])
            }
        }
        .padding(.horizontal, 20)
    }

    // Processing character — PillCharacter.active ile seçilir
    @ViewBuilder
    private var processingView: some View {
        switch PillCharacter.active {
        case .dots: DotsCharacter()
        case .face: FaceCharacter()
        }
    }

    private func startWaveTimer() {
        waveTimer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { _ in
            amplitudes = (0..<6).map { _ in CGFloat.random(in: 0.2...1.0) }
        }
    }
}

// MARK: - DotsCharacter
// 3 nokta, sırayla büyüyüp küçülür (bounce)

struct DotsCharacter: View {
    @State private var scales: [CGFloat] = [1, 1, 1]
    @State private var timer: Timer?

    var body: some View {
        HStack(spacing: 8) {
            ForEach(0..<3, id: \.self) { i in
                Circle()
                    .fill(Color.white)
                    .frame(width: 8, height: 8)
                    .scaleEffect(scales[i])
                    .animation(.easeInOut(duration: 0.25), value: scales[i])
            }
        }
        .onAppear { start() }
        .onDisappear { timer?.invalidate(); timer = nil }
    }

    private func start() {
        var step = 0
        timer = Timer.scheduledTimer(withTimeInterval: 0.25, repeats: true) { _ in
            scales = [1, 1, 1]
            scales[step % 3] = 1.7
            step += 1
        }
    }
}

// MARK: - FaceCharacter
// Gözler kırpıyor, ağız 3 ifade döngüsü: düz → gülümseme → dalgalı

struct FaceCharacter: View {
    @State private var isBlinking: Bool = false
    @State private var dotCount: Int = 0
    @State private var dotTimer: Timer?
    @State private var blinkTimer: Timer?

    var body: some View {
        ZStack {
            // Eyes
            HStack(spacing: 10) {
                Capsule()
                    .fill(Color.white.opacity(0.95))
                    .frame(width: 5, height: isBlinking ? 1 : 6)
                    .animation(.easeInOut(duration: 0.07), value: isBlinking)
                Capsule()
                    .fill(Color.white.opacity(0.95))
                    .frame(width: 5, height: isBlinking ? 1 : 6)
                    .animation(.easeInOut(duration: 0.07), value: isBlinking)
            }
            .offset(y: -6)

            // Mouth — 3 expression cycle
            MouthShape(phase: dotCount % 3)
                .stroke(Color.white.opacity(0.9), style: StrokeStyle(lineWidth: 2, lineCap: .round))
                .frame(width: 18, height: 10)
                .offset(y: 6)
        }
        .frame(width: 140, height: 48)
        .onAppear { start() }
        .onDisappear {
            dotTimer?.invalidate(); dotTimer = nil
            blinkTimer?.invalidate(); blinkTimer = nil
        }
    }

    private func start() {
        dotCount = 0
        isBlinking = false
        dotTimer = Timer.scheduledTimer(withTimeInterval: 1.2, repeats: true) { _ in
            dotCount += 1
        }
        blinkTimer = Timer.scheduledTimer(withTimeInterval: 2.5, repeats: true) { _ in
            isBlinking = true
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
                isBlinking = false
            }
        }
    }
}

// MARK: - MouthShape (FaceCharacter için)

private struct MouthShape: Shape {
    let phase: Int  // 0 = düz, 1 = gülümseme, 2 = dalgalı

    func path(in rect: CGRect) -> Path {
        var p = Path()
        let w = rect.width
        let h = rect.height
        switch phase {
        case 1: // gülümseme ∪
            p.move(to: CGPoint(x: 0, y: h * 0.2))
            p.addCurve(to: CGPoint(x: w, y: h * 0.2),
                       control1: CGPoint(x: w * 0.2, y: h),
                       control2: CGPoint(x: w * 0.8, y: h))
        case 2: // dalgalı ~
            p.move(to: CGPoint(x: 0, y: h * 0.5))
            p.addCurve(to: CGPoint(x: w * 0.5, y: h * 0.5),
                       control1: CGPoint(x: w * 0.1, y: 0),
                       control2: CGPoint(x: w * 0.4, y: h))
            p.addCurve(to: CGPoint(x: w, y: h * 0.5),
                       control1: CGPoint(x: w * 0.6, y: 0),
                       control2: CGPoint(x: w * 0.9, y: h))
        default: // düz —
            p.move(to: CGPoint(x: 0, y: h * 0.5))
            p.addLine(to: CGPoint(x: w, y: h * 0.5))
        }
        return p
    }
}
