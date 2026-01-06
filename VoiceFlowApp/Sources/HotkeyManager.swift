import AppKit
import Carbon

class HotkeyManager {
    var onDoubleTapFn: (() -> Void)?
    var onFnKeyDown: (() -> Void)?
    var onFnKeyUp: (() -> Void)?

    private var globalMonitor: Any?
    private var localMonitor: Any?

    private var lastFnPressTime: Date?
    private var isFnPressed = false
    private var isInPushToTalkMode = false

    private let doubleTapThreshold: TimeInterval = 0.3
    private let holdThreshold: TimeInterval = 0.15

    func start() {
        // Monitor for flagsChanged events (modifier keys including Fn)
        globalMonitor = NSEvent.addGlobalMonitorForEvents(matching: .flagsChanged) { [weak self] event in
            self?.handleFlagsChanged(event)
        }

        localMonitor = NSEvent.addLocalMonitorForEvents(matching: .flagsChanged) { [weak self] event in
            self?.handleFlagsChanged(event)
            return event
        }

        print("Hotkey manager started - Double-tap Fn for push-to-talk")
    }

    func stop() {
        if let monitor = globalMonitor {
            NSEvent.removeMonitor(monitor)
            globalMonitor = nil
        }
        if let monitor = localMonitor {
            NSEvent.removeMonitor(monitor)
            localMonitor = nil
        }
    }

    private func handleFlagsChanged(_ event: NSEvent) {
        // Check if Fn key state changed
        // Fn key is detected via the function key flag
        let fnPressed = event.modifierFlags.contains(.function)

        if fnPressed && !isFnPressed {
            // Fn key pressed down
            handleFnKeyDown()
        } else if !fnPressed && isFnPressed {
            // Fn key released
            handleFnKeyUp()
        }

        isFnPressed = fnPressed
    }

    private func handleFnKeyDown() {
        let now = Date()

        // Check for double-tap
        if let lastPress = lastFnPressTime,
           now.timeIntervalSince(lastPress) < doubleTapThreshold {
            // Double-tap detected - enter push-to-talk mode
            isInPushToTalkMode = true
            onDoubleTapFn?()
            onFnKeyDown?()
            lastFnPressTime = nil
        } else {
            lastFnPressTime = now

            // Schedule check for hold (single tap followed by hold)
            DispatchQueue.main.asyncAfter(deadline: .now() + holdThreshold) { [weak self] in
                guard let self = self else { return }
                if self.isFnPressed && self.lastFnPressTime != nil {
                    // Still holding after threshold - this is a hold, not a tap
                    // Don't trigger anything on single hold without double-tap
                }
            }
        }
    }

    private func handleFnKeyUp() {
        if isInPushToTalkMode {
            // Release after push-to-talk
            onFnKeyUp?()
            isInPushToTalkMode = false
        }
    }

    deinit {
        stop()
    }
}
