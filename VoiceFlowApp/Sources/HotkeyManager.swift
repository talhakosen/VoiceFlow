import AppKit
import Carbon

class HotkeyManager {
    /// Called when recording should start
    var onStartRecording: (() -> Void)?
    /// Called when recording should stop
    var onStopRecording: (() -> Void)?

    private var globalMonitor: Any?
    private var localMonitor: Any?

    private var lastFnDownTime: Date?
    private var isFnPressed = false
    private var isRecordingActive = false

    private let doubleTapThreshold: TimeInterval = 0.4

    func start() {
        globalMonitor = NSEvent.addGlobalMonitorForEvents(matching: .flagsChanged) { [weak self] event in
            self?.handleFlagsChanged(event)
        }

        localMonitor = NSEvent.addLocalMonitorForEvents(matching: .flagsChanged) { [weak self] event in
            self?.handleFlagsChanged(event)
            return event
        }

        NSLog("HotkeyManager: started - Double-tap Fn to toggle recording")
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
        let fnPressed = event.modifierFlags.contains(.function)

        if fnPressed && !isFnPressed {
            handleFnDown()
        } else if !fnPressed && isFnPressed {
            handleFnUp()
        }

        isFnPressed = fnPressed
    }

    private func handleFnDown() {
        let now = Date()

        if let last = lastFnDownTime,
           now.timeIntervalSince(last) < doubleTapThreshold {
            // Double-tap detected
            lastFnDownTime = nil

            if isRecordingActive {
                // Already recording → stop
                isRecordingActive = false
                NSLog("HotkeyManager: DOUBLE-TAP Fn → STOP recording")
                onStopRecording?()
            } else {
                // Not recording → start
                isRecordingActive = true
                NSLog("HotkeyManager: DOUBLE-TAP Fn → START recording")
                onStartRecording?()
            }
        } else {
            lastFnDownTime = now
        }
    }

    private func handleFnUp() {
        // Fn release also stops recording (push-to-talk fallback)
        if isRecordingActive {
            isRecordingActive = false
            NSLog("HotkeyManager: Fn RELEASED → STOP recording")
            onStopRecording?()
        }
    }

    func resetState() {
        isRecordingActive = false
        isFnPressed = false
        lastFnDownTime = nil
    }

    deinit {
        stop()
    }
}
