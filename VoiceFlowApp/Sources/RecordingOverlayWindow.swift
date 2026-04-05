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
        animationBehavior = .none

        let hostingView = SafeHostingView(rootView: RecordingPillView(state: pillState))
        hostingView.frame = NSRect(origin: .zero, size: VFLayout.Overlay.pill)
        contentView = hostingView
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
        let size = VFLayout.Overlay.pill
        let screenFrame = screen.visibleFrame
        let x = screenFrame.midX - size.width / 2
        let y = screenFrame.minY + VFLayout.overlayBottomInset
        setFrame(NSRect(x: x, y: y, width: size.width, height: size.height), display: false)
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
        .frame(width: VFLayout.Overlay.pill.width, height: VFLayout.Overlay.pill.height)
        .background(
            RoundedRectangle(cornerRadius: VFRadius.pill)
                .fill(VFColor.pillBackground)
        )
        .onChange(of: state.isProcessing) { _, processing in
            if processing { waveTimer?.invalidate(); waveTimer = nil }
            else { startWaveTimer() }
        }
        .onAppear { startWaveTimer() }
        .onDisappear { waveTimer?.invalidate(); waveTimer = nil }
    }

    private var waveformView: some View {
        HStack(spacing: VFSpacing.xs) {
            ForEach(0..<VFLayout.waveBarCount, id: \.self) { i in
                RoundedRectangle(cornerRadius: VFRadius.xs)
                    .fill(VFColor.pillForeground)
                    .frame(width: VFLayout.waveBarWidth,
                           height: max(VFLayout.waveBarMinHeight, amplitudes[i] * VFLayout.waveBarMaxHeight))
                    .animation(VFAnimation.wave, value: amplitudes[i])
            }
        }
        .padding(.horizontal, VFSpacing.xxxl)
    }

    @ViewBuilder
    private var processingView: some View {
        switch PillCharacter.active {
        case .dots: DotsCharacter()
        case .face: FaceCharacter()
        }
    }

    private func startWaveTimer() {
        waveTimer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { _ in
            amplitudes = (0..<VFLayout.waveBarCount).map { _ in CGFloat.random(in: 0.2...1.0) }
        }
    }
}

// MARK: - DotsCharacter

struct DotsCharacter: View {
    @State private var scales: [CGFloat] = Array(repeating: 1, count: VFLayout.dotCount)
    @State private var timer: Timer?

    var body: some View {
        HStack(spacing: VFSpacing.md) {
            ForEach(0..<VFLayout.dotCount, id: \.self) { i in
                Circle()
                    .fill(VFColor.pillForeground)
                    .frame(width: VFLayout.dotSize, height: VFLayout.dotSize)
                    .scaleEffect(scales[i])
                    .animation(VFAnimation.bounce, value: scales[i])
            }
        }
        .onAppear { start() }
        .onDisappear { timer?.invalidate(); timer = nil }
    }

    private func start() {
        var step = 0
        timer = Timer.scheduledTimer(withTimeInterval: 0.25, repeats: true) { _ in
            scales = Array(repeating: 1, count: VFLayout.dotCount)
            scales[step % VFLayout.dotCount] = VFLayout.dotScale
            step += 1
        }
    }
}

// MARK: - FaceCharacter
// Gözler kırpıyor, ağız 3 ifade döngüsü: düz → gülümseme → dalgalı

struct FaceCharacter: View {
    var body: some View {
        TimelineView(.animation) { tl in
            let t = tl.date.timeIntervalSinceReferenceDate
            let blinking = fmod(t, 2.5) < 0.1
            let mouthPhase = Int(t / 1.2) % 3
            ZStack {
                HStack(spacing: VFSpacing.lg) {
                    Capsule().fill(VFColor.pillEye)
                        .frame(width: VFLayout.eyeWidth, height: blinking ? 1 : VFLayout.eyeHeight)
                    Capsule().fill(VFColor.pillEye)
                        .frame(width: VFLayout.eyeWidth, height: blinking ? 1 : VFLayout.eyeHeight)
                }
                .offset(y: -6)
                MouthShape(phase: mouthPhase)
                    .stroke(VFColor.pillMouth, style: StrokeStyle(lineWidth: 2, lineCap: .round))
                    .frame(width: VFLayout.mouthWidth, height: VFLayout.mouthHeight)
                    .offset(y: 6)
            }
            .frame(width: VFLayout.Overlay.pill.width, height: VFLayout.Overlay.pill.height)
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
