import Foundation

/// Push-to-talk state machine — hold Fn to record, release to stop.
///
/// Tracks three states: idle, recording, processing.
/// `fnDown()` is blocked while recording OR processing — prevents stale events
/// from starting a new recording while the backend is still transcribing.
struct HotkeyStateMachine {
    var onStart: (() -> Void)?
    var onStop: (() -> Void)?

    private func log(_ msg: String) {
        let ts = ISO8601DateFormatter().string(from: Date())
        let line = "\(ts) [HotkeyStateMachine] \(msg)\n"
        print(line, terminator: "")
        if let data = line.data(using: .utf8),
           let fh = FileHandle(forWritingAtPath: "/tmp/voiceflow-hotkey.log") {
            fh.seekToEndOfFile(); fh.write(data); fh.closeFile()
        }
    }

    private(set) var isRecording = false
    private(set) var isProcessing = false
    private var startedAt: Date?   // when fnDown fired — protects against premature sync
    private var lastStopAt: Date?  // when fnUp fired — prevents immediate restart

    let cooldown: TimeInterval

    init(cooldown: TimeInterval = 0.3) {
        self.cooldown = cooldown
    }

    mutating func fnDown(at now: Date = Date()) {
        log("fnDown() — isRecording=\(isRecording) isProcessing=\(isProcessing)")
        guard !isRecording else {
            log("  → already recording, ignore")
            return
        }
        guard !isProcessing else {
            log("  → processing in progress, ignore")
            return
        }
        if let t = lastStopAt, now.timeIntervalSince(t) < cooldown {
            log("  → cooldown (\(String(format: "%.3f", now.timeIntervalSince(t)))s), ignore")
            return
        }
        isRecording = true
        startedAt = now
        log("  → onStart() firing")
        onStart?()
    }

    mutating func fnUp(at now: Date = Date()) {
        log("fnUp() — isRecording=\(isRecording)")
        guard isRecording else {
            log("  → not recording, ignore")
            return
        }
        isRecording = false
        startedAt = nil
        lastStopAt = now
        log("  → onStop() firing")
        onStop?()
    }

    /// Called by AppDelegate when TCA transitions to/from processing state.
    mutating func setProcessing(_ processing: Bool) {
        guard isProcessing != processing else { return }
        log("setProcessing(\(processing))")
        isProcessing = processing
        if !processing {
            // Reset lastStopAt so cooldown doesn't block the next recording
            // after processing finishes (processing can take 3-5s).
            lastStopAt = Date()
        }
    }

    /// Correct drift between HotkeyManager and TCA.
    /// Blocked for 2s after any start or stop — gives TCA time to process async actions.
    mutating func sync(tcaIsRecording: Bool, at now: Date = Date()) {
        guard isRecording != tcaIsRecording else { return }
        if let t = startedAt,  now.timeIntervalSince(t) < 2.0 {
            log("sync blocked — startedAt grace (\(String(format: "%.2f", now.timeIntervalSince(t)))s)")
            return
        }
        if let t = lastStopAt, now.timeIntervalSince(t) < 2.0 {
            log("sync blocked — lastStopAt grace (\(String(format: "%.2f", now.timeIntervalSince(t)))s)")
            return
        }
        log("sync: isRecording \(isRecording) → \(tcaIsRecording)")
        isRecording = tcaIsRecording
        if !tcaIsRecording { startedAt = nil }
    }

    mutating func reset() {
        log("reset()")
        isRecording = false
        isProcessing = false
        startedAt = nil
        lastStopAt = Date()
    }
}
