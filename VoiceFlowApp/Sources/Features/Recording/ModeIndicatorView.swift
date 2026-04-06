import SwiftUI
import AppKit

// MARK: - ModeIndicatorView
// Large floating badge shown in top-right corner:
//   • While recording (Fn held) — stays until recording ends
//   • On mode switch — shows 2 seconds then auto-hides

struct ModeIndicatorView: View {
    let mode: AppMode

    var body: some View {
        Image(systemName: mode.indicatorIcon)
            .font(VFFont.pillIcon)
            .foregroundStyle(mode.color)
        .padding(VFSpacing.xxl)
        .background(
            ZStack {
                Capsule().fill(.ultraThinMaterial)
                Capsule().fill(VFColor.fill(mode.color))
                Capsule().strokeBorder(VFColor.border(mode.color), lineWidth: 1.5)
            }
        )
        .vfAccentShadow(accent: mode.color)
    }
}

// MARK: - ModeIndicatorWindowController

final class ModeIndicatorWindowController: NSObject {
    private var panel: NSPanel?
    private var autoDismissTask: Task<Void, Never>?

    /// Show while recording — stays until `close()` is called.
    func showPersistent(mode: AppMode) {
        autoDismissTask?.cancel()
        autoDismissTask = nil
        _show(mode: mode)
    }

    /// Show briefly after mode switch — auto-hides after 2 seconds.
    func showBriefly(mode: AppMode) {
        autoDismissTask?.cancel()
        _show(mode: mode)
        autoDismissTask = Task { [weak self] in
            try? await Task.sleep(nanoseconds: 2_000_000_000)
            guard !Task.isCancelled else { return }
            self?.close()
        }
    }

    func close() {
        autoDismissTask?.cancel()
        autoDismissTask = nil
        DispatchQueue.main.async { [weak self] in
            self?.panel?.orderOut(nil)
            self?.panel = nil
        }
    }

    private func _show(mode: AppMode) {
        DispatchQueue.main.async { [weak self] in
            guard let self else { return }

            let view = ModeIndicatorView(mode: mode)

            if let existing = self.panel {
                (existing.contentView as? NSHostingView<ModeIndicatorView>)?.rootView = view
                existing.orderFront(nil)
                return
            }

            // Fixed size: icon(18) + inner-padding(16×2) + shadow(8) ≈ 66px square
            let s = VFLayout.Overlay.modeIndicatorPill
            let p = NSPanel(
                contentRect: NSRect(origin: .zero, size: s),
                styleMask: [.borderless, .nonactivatingPanel],
                backing: .buffered,
                defer: false
            )
            p.isFloatingPanel = true
            p.level = .floating
            p.backgroundColor = .clear
            p.isOpaque = false
            p.hasShadow = false
            p.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]

            let hosting = NSHostingView(rootView: view)
            p.contentView = hosting

            if let screen = NSScreen.main {
                let sw = screen.visibleFrame
                p.setFrameOrigin(NSPoint(
                    x: sw.maxX - s.width  - VFLayout.overlayEdgeInset,
                    y: sw.maxY - s.height - VFLayout.overlayEdgeInset
                ))
            }
            p.orderFront(nil)
            self.panel = p
        }
    }
}
