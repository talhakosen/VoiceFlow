import AppKit
import Carbon

class HotkeyManager {
    private static let logFile: FileHandle? = {
        let path = "/tmp/voiceflow-hotkey.log"
        FileManager.default.createFile(atPath: path, contents: nil)
        return FileHandle(forWritingAtPath: path)
    }()

    private func log(_ msg: String) {
        let ts = ISO8601DateFormatter().string(from: Date())
        let line = "\(ts) \(msg)\n"
        Self.logFile?.seekToEndOfFile()
        Self.logFile?.write(line.data(using: .utf8)!)
    }
    /// Called when recording should start
    var onStartRecording: (() -> Void)?
    /// Called when recording should stop
    var onStopRecording: (() -> Void)?

    private var globalMonitor: Any?
    private var localMonitor: Any?

    private var lastFnDownTime: Date?
    private var isFnPressed = false
    private var isRecordingActive = false
    private var lastActionTime: Date?

    private let doubleTapThreshold: TimeInterval = 0.4
    private let cooldownAfterAction: TimeInterval = 0.8

    func start() {
        globalMonitor = NSEvent.addGlobalMonitorForEvents(matching: .flagsChanged) { [weak self] event in
            self?.handleFlagsChanged(event)
        }

        localMonitor = NSEvent.addLocalMonitorForEvents(matching: .flagsChanged) { [weak self] event in
            self?.handleFlagsChanged(event)
            return event
        }

        log(" started - Double-tap Fn to toggle recording")
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
        let rawFlags = event.modifierFlags.rawValue

        log("flags fn=\(fnPressed ? "Y":"N") wasFn=\(isFnPressed ? "Y":"N") raw=0x\(String(rawFlags, radix:16)) rec=\(isRecordingActive ? "Y":"N")")

        if fnPressed && !isFnPressed {
            handleFnDown()
        } else if fnPressed && isFnPressed {
            // Fn down again while we think it's already down = we missed the release (macOS swallowed it)
            log(" Fn DOWN but isFnPressed=true → missed release, treating as new press")
            isFnPressed = false
            handleFnDown()
        } else if !fnPressed && isFnPressed {
            handleFnUp()
        }

        isFnPressed = fnPressed
    }

    private func handleFnDown() {
        let now = Date()

        // Cooldown after start/stop to prevent accidental re-trigger
        if let lastAction = lastActionTime,
           now.timeIntervalSince(lastAction) < cooldownAfterAction {
            log(" Fn DOWN → IGNORED (cooldown)")
            lastFnDownTime = nil
            return
        }

        if let last = lastFnDownTime,
           now.timeIntervalSince(last) < doubleTapThreshold {
            // Double-tap detected
            lastFnDownTime = nil
            lastActionTime = now

            if isRecordingActive {
                // Already recording → stop
                isRecordingActive = false
                log(" DOUBLE-TAP Fn → STOP recording")
                onStopRecording?()
            } else {
                // Not recording → start
                isRecordingActive = true
                log(" DOUBLE-TAP Fn → START recording")
                onStartRecording?()
            }
        } else {
            lastFnDownTime = now
        }
    }

    private func handleFnUp() {
        // During cooldown after a start/stop action, ignore releases
        if let lastAction = lastActionTime,
           Date().timeIntervalSince(lastAction) < cooldownAfterAction {
            log(" Fn RELEASED → IGNORED (cooldown)")
            return
        }

        // Within double-tap window, don't stop (user might be mid-double-tap)
        if let last = lastFnDownTime, Date().timeIntervalSince(last) < doubleTapThreshold {
            log(" Fn RELEASED → IGNORED (within double-tap window)")
            return
        }

        // Fn release stops recording (push-to-talk)
        if isRecordingActive {
            isRecordingActive = false
            lastActionTime = Date()
            log(" Fn RELEASED → STOP recording")
            onStopRecording?()
        }
    }

    func resetState() {
        isRecordingActive = false
        isFnPressed = false
        lastFnDownTime = nil
        lastActionTime = nil
    }

    deinit {
        stop()
    }
}
