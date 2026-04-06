import AppKit

/// Thin NSEvent wrapper around HotkeyStateMachine.
/// macOS fires spurious DOWN→UP→DOWN bursts while Fn is held.
/// We debounce the UP: only mark key as released if no DOWN arrives within 250ms.
class HotkeyManager {
    var onStartRecording: (() -> Void)? { didSet { sm.onStart = onStartRecording } }
    var onStopRecording: (() -> Void)?  { didSet { sm.onStop  = onStopRecording  } }
    var onSwitchMode: ((Int) -> Void)?

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
        let keys = NSEvent.addGlobalMonitorForEvents(matching: .keyDown) { [weak self] event in
            guard event.modifierFlags.intersection([.option, .command, .control, .shift]) == .option else { return }
            switch event.keyCode {
            case 18: self?.onSwitchMode?(0)
            case 19: self?.onSwitchMode?(1)
            case 20: self?.onSwitchMode?(2)
            default: break
            }
        }

        monitors = [flags, local, keys].compactMap { $0 }
        log("monitors registered: \(monitors.count) (flags=\(flags != nil), local=\(local != nil), keys=\(keys != nil))")

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
