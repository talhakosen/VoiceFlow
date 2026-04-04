import SwiftUI
import AppKit

// MARK: - ModeIndicatorView
// Large floating badge shown in top-right corner:
//   • While recording (Fn held) — stays until recording ends
//   • On mode switch — shows 2 seconds then auto-hides

struct ModeIndicatorView: View {
    let mode: AppMode

    private var modeColor: Color {
        switch mode {
        case .general:     return .blue
        case .engineering: return .green
        case .office:      return .orange
        }
    }

    private var modeIcon: String {
        switch mode {
        case .general:     return "text.bubble.fill"
        case .engineering: return "chevron.left.forwardslash.chevron.right"
        case .office:      return "envelope.fill"
        }
    }

    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: modeIcon)
                .font(.system(size: 18, weight: .semibold))
                .foregroundStyle(modeColor)

            Text(mode.displayName)
                .font(.system(size: 17, weight: .semibold, design: .rounded))
                .foregroundStyle(.white)
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 14)
        .background(
            ZStack {
                Capsule().fill(.ultraThinMaterial)
                Capsule().fill(modeColor.opacity(0.18))
                Capsule().strokeBorder(modeColor.opacity(0.45), lineWidth: 1.5)
            }
        )
        .shadow(color: modeColor.opacity(0.35), radius: 16, x: 0, y: 4)
        .shadow(color: .black.opacity(0.25), radius: 8, x: 0, y: 2)
        .padding(20)
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

            let hosting = NSHostingView(rootView: ModeIndicatorView(mode: mode))
            hosting.sizingOptions = [.preferredContentSize]

            if let existing = self.panel {
                existing.contentView = hosting
                existing.orderFront(nil)
                return
            }

            let p = NSPanel(
                contentRect: NSRect(x: 0, y: 0, width: 220, height: 60),
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
