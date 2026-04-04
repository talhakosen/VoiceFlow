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
        alphaValue = 0  // başlangıçta gizli — view canlı, task çalışır

        let hostingView = SafeHostingView(rootView: RecordingPillView(state: pillState))
        hostingView.frame = NSRect(origin: .zero, size: VFLayout.Overlay.pill)
        contentView = hostingView
        reposition()
        orderFrontRegardless()  // her zaman window listesinde — orderOut yok
    }

    func showRecording() {
        pillState.isProcessing = false
        alphaValue = 1
    }

    func showProcessing() {
        pillState.isProcessing = true
        alphaValue = 1
    }

    func hide() {
        alphaValue = 0
        pillState.isProcessing = false
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

    var body: some View {
        ZStack {
            if state.isProcessing {
                DotsCharacter()
            } else {
                WaveformView()
            }
        }
        .frame(width: VFLayout.Overlay.pill.width, height: VFLayout.Overlay.pill.height)
        .background(
            RoundedRectangle(cornerRadius: VFRadius.pill)
                .fill(VFColor.pillBackground)
        )
    }
}

// MARK: - WaveformView — TimelineView driven, no Timer/Task

private struct WaveformView: View {
    // Her bar için sabit faz ofseti — her render'da farklı amplitüd verir
    private let phases: [Double] = (0..<VFLayout.waveBarCount).map { Double($0) * 0.9 + 0.3 }
    private let speeds: [Double] = (0..<VFLayout.waveBarCount).map { Double($0) * 0.4 + 1.1 }

    var body: some View {
        TimelineView(.animation) { tl in
            let t = tl.date.timeIntervalSinceReferenceDate
            HStack(spacing: VFSpacing.xs) {
                ForEach(0..<VFLayout.waveBarCount, id: \.self) { i in
                    let amp = (sin(t * speeds[i] + phases[i]) + 1) / 2  // 0…1
                    let h = VFLayout.waveBarMinHeight + amp * (VFLayout.waveBarMaxHeight - VFLayout.waveBarMinHeight)
                    RoundedRectangle(cornerRadius: VFRadius.xs)
                        .fill(VFColor.pillForeground)
                        .frame(width: VFLayout.waveBarWidth, height: h)
                }
            }
            .padding(.horizontal, VFSpacing.xxxl)
        }
    }
}

// MARK: - DotsCharacter — TimelineView driven

struct DotsCharacter: View {
    var body: some View {
        TimelineView(.periodic(from: .now, by: 0.28)) { tl in
            let step = Int(tl.date.timeIntervalSinceReferenceDate / 0.28) % VFLayout.dotCount
            HStack(spacing: VFSpacing.md) {
                ForEach(0..<VFLayout.dotCount, id: \.self) { i in
                    Circle()
                        .fill(VFColor.pillForeground)
                        .frame(width: VFLayout.dotSize, height: VFLayout.dotSize)
                        .scaleEffect(i == step ? VFLayout.dotScale : 1)
                        .animation(VFAnimation.bounce, value: step)
                }
            }
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
