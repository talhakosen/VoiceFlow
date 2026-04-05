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
        .padding(VFSpacing.xxxl)
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

            let hosting = SafeHostingView(rootView: ModeIndicatorView(mode: mode))
            hosting.sizingOptions = [.preferredContentSize]

            if let existing = self.panel {
                existing.contentView = hosting
                existing.orderFront(nil)
                return
            }

            let p = NSPanel(
                contentRect: NSRect(origin: .zero, size: VFLayout.Overlay.modeIndicator),
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
                    x: sw.maxX - p.frame.width - 20,
                    y: sw.maxY - p.frame.height - 20
                ))
            }

            p.orderFront(nil)
            self.panel = p
        }
    }
}
