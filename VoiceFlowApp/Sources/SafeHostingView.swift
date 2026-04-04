import AppKit
import SwiftUI

/// NSHostingView subclass for use inside borderless nonactivatingPanel.
/// Overrides setNeedsUpdateConstraints() to prevent EXC_BREAKPOINT crash
/// when SwiftUI animations/state changes trigger constraint invalidation on
/// _postWindowNeedsUpdateConstraints.
final class SafeHostingView<Content: View>: NSHostingView<Content> {
    override var needsUpdateConstraints: Bool {
        get { super.needsUpdateConstraints }
        set { /* no-op: borderless nonactivatingPanel + SwiftUI constraint updates
                 cause _postWindowNeedsUpdateConstraints EXC_BREAKPOINT crash */ }
    }
}
