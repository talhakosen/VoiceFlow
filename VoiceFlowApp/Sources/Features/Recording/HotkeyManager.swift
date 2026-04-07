import AppKit

/// Thin NSEvent wrapper around HotkeyStateMachine.
/// macOS fires spurious DOWN→UP→DOWN bursts while Fn is held.
/// We debounce the UP: only mark key as released if no DOWN arrives within 250ms.
class HotkeyManager {
    var onStartRecording: (() -> Void)? { didSet { sm.onStart = onStartRecording } }
    var onStopRecording: (() -> Void)?  { didSet { sm.onStop  = onStopRecording  } }
    var onModeSwitch: ((AppMode) -> Void)?

    private var sm = HotkeyStateMachine()
    private var monitors: [Any] = []
    private var fnUpWork: DispatchWorkItem?
    private var monitorStartedAt: Date = .distantPast

    private func log(_ msg: String) {
        let ts = ISO8601DateFormatter().string(from: Date())
        let line = "\(ts) [HotkeyManager] \(msg)\n"
        print(line, terminator: "")
        if let data = line.data(using: .utf8) {
            if let fh = FileHandle(forWritingAtPath: "/tmp/voiceflow-hotkey.log") {
                fh.seekToEndOfFile(); fh.write(data); fh.closeFile()
            } else {
                // Log file doesn't exist yet, create it
                try? data.write(to: URL(fileURLWithPath: "/tmp/voiceflow-hotkey.log"))
            }
        }
    }

    func start() {
        stop()  // clear any orphaned monitors from previous calls
        monitorStartedAt = Date()
        log("start() called — registering monitors")

        let flags = NSEvent.addGlobalMonitorForEvents(matching: .flagsChanged) { [weak self] in
            self?.handle($0, source: "global")
        }
        let local = NSEvent.addLocalMonitorForEvents(matching: .flagsChanged) { [weak self] event in
            self?.handle(event, source: "local")
            return event
        }
        // Option+1/2/3 global mode switching (keyDown with ⌥ modifier)
        let keyGlobal = NSEvent.addGlobalMonitorForEvents(matching: .keyDown) { [weak self] in
            self?.handleModeKey($0)
        }
        let keyLocal = NSEvent.addLocalMonitorForEvents(matching: .keyDown) { [weak self] event in
            if self?.handleModeKey(event) == true { return nil }
            return event
        }
        monitors = [flags, local, keyGlobal, keyLocal].compactMap { $0 }
        log("monitors registered: \(monitors.count) (flags=\(flags != nil), local=\(local != nil))")

        if flags == nil {
            log("⚠️ GLOBAL MONITOR IS NIL — Accessibility permission missing!")
        }
    }

    func stop() {
        log("stop() called — removing \(monitors.count) monitors")
        fnUpWork?.cancel()
        fnUpWork = nil
        monitors.forEach { NSEvent.removeMonitor($0) }
        monitors = []
    }

    func resetState() {
        log("resetState() called")
        sm.reset()
    }

    func syncRecordingState(_ tcaIsRecording: Bool) {
        sm.sync(tcaIsRecording: tcaIsRecording)
    }

    func setProcessing(_ processing: Bool) {
        sm.setProcessing(processing)
    }

    /// Returns true if event was consumed (⌥1/2/3 mode switch).
    @discardableResult
    private func handleModeKey(_ event: NSEvent) -> Bool {
        guard event.modifierFlags.contains(.option),
              !event.modifierFlags.contains(.command),
              !event.modifierFlags.contains(.control) else { return false }
        let modes = AppMode.allCases  // [general, engineering, office]
        // keyCodes: 1→18, 2→19, 3→20
        let index: Int
        switch event.keyCode {
        case 18: index = 0
        case 19: index = 1
        case 20: index = 2
        default: return false
        }
        guard index < modes.count else { return false }
        let mode = modes[index]
        log("⌥\(index + 1) → mode switch to \(mode.rawValue)")
        onModeSwitch?(mode)
        return true
    }

    private func handle(_ event: NSEvent, source: String) {
        let fn = event.modifierFlags.contains(.function)
        log("flagsChanged [\(source)] fn=\(fn) smRecording=\(sm.isRecording) raw=0x\(String(event.modifierFlags.rawValue, radix: 16))")

        if fn {
            // Ignore stale fn=true events delivered right after monitor re-registration
            guard Date().timeIntervalSince(monitorStartedAt) > 0.3 else {
                log("  → ignoring stale fn=true within 300ms of start()")
                return
            }
            // Cancel any pending UP — key is still held
            fnUpWork?.cancel()
            fnUpWork = nil
            // SM ignores if already recording — no isFnPressed guard needed
            sm.fnDown()
        } else {
            // Debounce: macOS fires spurious UPs while Fn is held.
            // Only call fnUp if no DOWN arrives within 250ms.
            fnUpWork?.cancel()
            let work = DispatchWorkItem { [weak self] in
                guard let self else { return }
                self.log("  → debounce fired, calling sm.fnUp()")
                self.sm.fnUp()
            }
            fnUpWork = work
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.25, execute: work)
        }
    }

    deinit { stop() }
}
