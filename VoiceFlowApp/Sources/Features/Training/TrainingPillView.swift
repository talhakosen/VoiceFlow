import ComposableArchitecture
import SwiftUI
import AppKit

// MARK: - TrainingPillView
// Floating "Düzelt" button — bottom-right corner, semi-transparent, 10s countdown.

struct TrainingPillView: View {
    let store: StoreOf<AppFeature>

    // Fix 2: TrainingFeature is sole owner of pill state; read from store.training
    private var displayText: String { store.training.originalText }
    private var countdown: Int { store.training.countdown }

    private var accent: Color { VFColor.primary }

    var body: some View {
        Button {
            store.send(.training(.editTapped))
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
