import AppKit
import ComposableArchitecture
import SwiftUI

class AppDelegate: NSObject, NSApplicationDelegate {
    private var menuBarController: MenuBarController?
    private var recordingOverlay: RecordingOverlayWindow?
    private var backendProcess: Process?
    private let backendPort = 8765
    private var healthCheckTimer: Timer?
    private var onboardingWindow: NSWindow?
    private var loginWindow: NSPanel?
    private let trainingPillController = TrainingPillWindowController()
    private let modeIndicator = ModeIndicatorWindowController()
    private let symbolPicker = SymbolPickerWindowController()

    // Single TCA store — created once, injected everywhere
    let store = Store(initialState: AppFeature.State()) { AppFeature() }

    private var storeObservation: Task<Void, Never>?
    private let hotkeyManager = HotkeyManager()

    func applicationDidFinishLaunching(_ notification: Notification) {
        ensureUserID()

        let overlay = RecordingOverlayWindow()
        self.recordingOverlay = overlay

        // Wire HotkeyManager → TCA store
        hotkeyManager.onStartRecording = { [weak self] in
            self?.store.send(.recording(.startRecording))
        }
        hotkeyManager.onStopRecording = { [weak self] in
            self?.store.send(.recording(.stopRecording))
        }
        hotkeyManager.onSwitchMode = { [weak self] index in
            let modes = AppMode.allCases
            guard index < modes.count else { return }
            self?.store.send(.recording(.selectAppMode(modes[index])))
        }
        hotkeyManager.start()

        // Observe store state to drive overlay and mode indicator windows
        storeObservation = Task { @MainActor [weak self] in
            guard let self else { return }
            // Polling loop — observe TCA state changes
            var prevRecording = false
            var prevProcessing = false
            var prevShowPill = false
            var prevMode: AppMode = .general

            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 100_000_000) // 100ms
                let recState = self.store.recording
                let isRecording = recState.isRecording
                let isProcessing = recState.isProcessing
                // Fix 2: Training pill visibility is owned by TrainingFeature, not RecordingFeature
                let showPill = self.store.training.isVisible
                let mode = recState.currentAppMode

                if isRecording && !prevRecording {
                    overlay.showRecording()
                    self.modeIndicator.showPersistent(mode: mode)
                } else if isProcessing && !prevProcessing {
                    overlay.showProcessing()
                    self.modeIndicator.close()
                } else if !isRecording && !isProcessing && (prevRecording || prevProcessing) {
                    overlay.hide()
                    self.modeIndicator.close()
                }

                if mode != prevMode && !isRecording {
                    self.modeIndicator.showBriefly(mode: mode)
                }

                if showPill && !prevShowPill {
                    self.trainingPillController.show(store: self.store)
                } else if !showPill && prevShowPill {
                    self.trainingPillController.close()
                }

                prevRecording = isRecording
                prevProcessing = isProcessing
                prevShowPill = showPill
                prevMode = mode
            }
        }

        // Wire backend restart callbacks into store effects via observation
        // AppDelegate owns backend lifecycle — inject closures via environment or direct call
        // We use notifications / callbacks stored on AppDelegate for restart
        store.send(.recording(.restartBackend)) // no-op start; real restart wired below

        let mode = UserDefaults.standard.string(forKey: AppSettings.deploymentMode) ?? "local"

        if mode == "server" {
            NSLog("VoiceFlow: Server mode — skipping local backend startup")
            DispatchQueue.main.async {
                self.menuBarController = MenuBarController(store: self.store)
            }
        } else {
            killExistingBackend()
            startBackend()
            waitForBackendReady { [weak self] success in
                DispatchQueue.main.async {
                    NSLog("VoiceFlow: Backend %@", success ? "ready" : "may not be ready")
                    if !success {
                        self?.store.send(.recording(.recordingFailed("Servis başlatılamadı — Yeniden Başlat'a bas")))
                    }
                    guard let self else { return }
                    self.menuBarController = MenuBarController(store: self.store)
                }
            }
        }

        requestAccessibilityPermission()

        let deployMode = UserDefaults.standard.string(forKey: AppSettings.deploymentMode) ?? "local"
        if deployMode == "server" {
            store.send(.auth(.tokenRefreshAttempted))
            Task { @MainActor [weak self] in
                guard let self else { return }
                try? await Task.sleep(nanoseconds: 300_000_000)
                if !self.store.auth.isLoggedIn {
                    self.showLoginWindow()
                }
                while !self.store.auth.isLoggedIn {
                    try? await Task.sleep(nanoseconds: 200_000_000)
                }
                self.loginWindow?.close()
                self.loginWindow = nil
                self.showOnboardingIfNeeded()
            }
        } else {
            showOnboardingIfNeeded()
        }
    }

    private func showLoginWindow() {
        let authStore = store.scope(state: \.auth, action: \.auth)
        let hosting = NSHostingController(rootView: LoginView(store: authStore))
        let panel = NSPanel(
            contentRect: NSRect(origin: .zero, size: VFLayout.WindowSize.login),
            styleMask: [.titled, .fullSizeContentView, .nonactivatingPanel],
            backing: .buffered,
            defer: false
        )
        panel.contentViewController = hosting
        panel.title = "VoiceFlow Giriş"
        panel.isReleasedWhenClosed = false
        panel.isMovableByWindowBackground = true
        panel.center()
        panel.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        loginWindow = panel
    }

    private func showOnboardingIfNeeded() {
        let complete = UserDefaults.standard.bool(forKey: AppSettings.onboardingComplete)
        guard !complete else { return }

        let view = OnboardingView(onComplete: { [weak self] in
            self?.onboardingWindow?.close()
            self?.onboardingWindow = nil
        })
        let hosting = NSHostingController(rootView: view)
        let window = NSWindow(
            contentRect: NSRect(origin: .zero, size: VFLayout.WindowSize.onboarding),
            styleMask: [.titled, .closable],
            backing: .buffered,
            defer: false
        )
        window.contentViewController = hosting
        window.title = "VoiceFlow'a Hoş Geldiniz"
        window.isReleasedWhenClosed = false
        window.center()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        onboardingWindow = window
    }

    func applicationWillTerminate(_ notification: Notification) {
        healthCheckTimer?.invalidate()
        storeObservation?.cancel()
        hotkeyManager.stop()
        stopBackend()
    }

    // MARK: - Backend Lifecycle

    /// Kill all processes on backendPort. SIGTERM first, SIGKILL after 1s. Blocks until port free (max 4s).
    private func killExistingBackend() {
        // Step 1: SIGTERM graceful
        shellKillPort(backendPort, signal: "TERM")
        Thread.sleep(forTimeInterval: 1.0)

        // Step 2: SIGKILL if still alive
        if !pidsOnPort(backendPort).isEmpty {
            shellKillPort(backendPort, signal: "KILL")
            NSLog("VoiceFlow: SIGKILL sent to port %d", backendPort)
        }

        // Step 3: Wait up to 3s for port to free
        for _ in 0..<30 {
            if pidsOnPort(backendPort).isEmpty { break }
            Thread.sleep(forTimeInterval: 0.1)
        }
        NSLog("VoiceFlow: Port %d is %@", backendPort, pidsOnPort(backendPort).isEmpty ? "free" : "still in use!")
    }

    /// Shell-based kill — more reliable than Swift Process for SIGKILL on stubborn pids.
    private func shellKillPort(_ port: Int, signal: String) {
        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/bin/bash")
        task.arguments = ["-c", "lsof -nP -iTCP:\(port) -sTCP:LISTEN -t 2>/dev/null | xargs kill -\(signal) 2>/dev/null"]
        task.standardOutput = Pipe()
        task.standardError = Pipe()
        try? task.run()
        task.waitUntilExit()
    }

    /// Returns PIDs of processes in TCP LISTEN state on the given port.
    /// Uses -sTCP:LISTEN to avoid matching processes that merely connect to the port.
    private func pidsOnPort(_ port: Int) -> [Int32] {
        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/usr/bin/lsof")
        task.arguments = ["-nP", "-iTCP:\(port)", "-sTCP:LISTEN", "-t"]
        let pipe = Pipe()
        task.standardOutput = pipe
        task.standardError = Pipe()
        do {
            try task.run()
            task.waitUntilExit()
            let output = String(data: pipe.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
            return output.components(separatedBy: "\n").compactMap { Int32($0.trimmingCharacters(in: .whitespaces)) }
        } catch {
            return []
        }
    }

    private func startBackend() {
        let backendPath = findBackendPath()
        NSLog("VoiceFlow: Backend path: %@", backendPath)
        guard let pythonPath = findPythonPath() else {
            NSLog("VoiceFlow: ERROR - Python not found!")
            return
        }
        NSLog("VoiceFlow: Python path: %@", pythonPath)

        backendProcess = Process()
        backendProcess?.executableURL = URL(fileURLWithPath: pythonPath)
        backendProcess?.arguments = ["-m", "voiceflow.main"]
        backendProcess?.currentDirectoryURL = URL(fileURLWithPath: backendPath)

        // Set up environment for venv
        var env = ProcessInfo.processInfo.environment
        let venvPath = "\(backendPath)/.venv"
        env["VIRTUAL_ENV"] = venvPath
        env["PATH"] = "\(venvPath)/bin:" + (env["PATH"] ?? "")
        env["PYTHONPATH"] = "\(backendPath)/src"
        env["HF_TOKEN"] = env["HF_TOKEN"] ?? ""

        let llmMode = UserDefaults.standard.string(forKey: AppSettings.llmMode) ?? "local"
        // Parse .env file once
        let projectRoot = URL(fileURLWithPath: backendPath).deletingLastPathComponent().path
        var dotEnv: [String: String] = [:]
        if let contents = try? String(contentsOfFile: "\(projectRoot)/.env", encoding: .utf8) {
            for line in contents.components(separatedBy: "\n") {
                let trimmed = line.trimmingCharacters(in: .whitespaces)
                guard !trimmed.hasPrefix("#"), !trimmed.isEmpty else { continue }
                let parts = trimmed.components(separatedBy: "=")
                if parts.count >= 2 {
                    dotEnv[parts[0].trimmingCharacters(in: .whitespaces)] = parts[1...].joined(separator: "=").trimmingCharacters(in: .whitespaces)
                }
            }
        }

        if llmMode == "cloud" {
            env["LLM_BACKEND"] = "ollama"
            for key in ["LLM_ENDPOINT", "LLM_MODEL", "HF_TOKEN"] {
                if let val = dotEnv[key] { env[key] = val }
            }
            NSLog("VoiceFlow: LLM_BACKEND=ollama (RunPod), LLM_ENDPOINT=%@", env["LLM_ENDPOINT"] ?? "nil")
        } else if llmMode == "alibaba" {
            env["LLM_BACKEND"] = "ollama"
            env["LLM_ENDPOINT"] = "https://dashscope-intl.aliyuncs.com/compatible-mode"
            env["LLM_MODEL"] = "qwen-max"
            if let apiKey = dotEnv["ALIBABA_API_KEY"] { env["LLM_API_KEY"] = apiKey }
            NSLog("VoiceFlow: LLM_BACKEND=ollama (Alibaba DashScope), model=qwen-max")
        } else {
            env["LLM_BACKEND"] = "mlx"
            // LoRA adapter — local mode only
            if let adapterPath = dotEnv["LLM_ADAPTER_PATH"] {
                env["LLM_ADAPTER_PATH"] = adapterPath
                NSLog("VoiceFlow: LoRA adapter: %@", adapterPath)
            }
        }

        backendProcess?.environment = env

        // Redirect stdout+stderr to log file
        let logPath = "/tmp/voiceflow.log"
        FileManager.default.createFile(atPath: logPath, contents: nil)
        let logHandle = FileHandle(forWritingAtPath: logPath)!
        logHandle.seekToEndOfFile()
        backendProcess?.standardOutput = logHandle
        backendProcess?.standardError = logHandle

        do {
            try backendProcess?.run()
            NSLog("VoiceFlow: Backend started with PID: %d", backendProcess?.processIdentifier ?? 0)
        } catch {
            NSLog("VoiceFlow: Failed to start backend: %@", error.localizedDescription)
        }
    }

    private func waitForBackendReady(maxAttempts: Int = 30, completion: @escaping (Bool) -> Void) {
        var attempts = 0

        healthCheckTimer = Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { [weak self] timer in
            attempts += 1

            guard let self = self else {
                timer.invalidate()
                completion(false)
                return
            }

            // Check if process died
            if let process = self.backendProcess, !process.isRunning {
                timer.invalidate()
                print("Backend process died")
                completion(false)
                return
            }

            // Try health check
            self.checkBackendHealth { isHealthy in
                if isHealthy {
                    timer.invalidate()
                    completion(true)
                } else if attempts >= maxAttempts {
                    timer.invalidate()
                    print("Backend health check timed out after \(attempts) attempts")
                    completion(false)
                }
            }
        }
    }

    private func checkBackendHealth(completion: @escaping (Bool) -> Void) {
        guard let url = URL(string: "http://127.0.0.1:\(backendPort)/health") else {
            completion(false)
            return
        }

        let task = URLSession.shared.dataTask(with: url) { _, response, _ in
            if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 {
                completion(true)
            } else {
                completion(false)
            }
        }
        task.resume()
    }

    /// Hard reset: SIGKILL everything on backendPort (including voiceflow), then restart fresh.
    func hardResetBackend(completion: @escaping (Bool) -> Void) {
        DispatchQueue.global().async { [weak self] in
            guard let self else { return }
            // Kill own process reference first
            if let p = self.backendProcess, p.isRunning { p.terminate() }
            self.backendProcess = nil
            // SIGKILL everything on port — no grace period
            let pids = self.pidsOnPort(self.backendPort)
            for pid in pids {
                kill(pid, SIGKILL)
                NSLog("VoiceFlow: Hard reset SIGKILL pid %d", pid)
            }
            // Wait for port to free
            for _ in 0..<30 {
                if self.pidsOnPort(self.backendPort).isEmpty { break }
                Thread.sleep(forTimeInterval: 0.1)
            }
            NSLog("VoiceFlow: Hard reset — port %d %@", self.backendPort,
                  self.pidsOnPort(self.backendPort).isEmpty ? "free" : "still in use!")
            DispatchQueue.main.async {
                self.startBackend()
                self.waitForBackendReady { success in
                    DispatchQueue.main.async {
                        NSLog("VoiceFlow: Hard reset restart %@", success ? "succeeded" : "failed")
                        completion(success)
                    }
                }
            }
        }
    }

    /// Public restart method — soft kill first, escalates to SIGKILL if port still occupied.
    func restartBackend(completion: ((Bool) -> Void)? = nil) {
        NSLog("VoiceFlow: Restarting backend...")
        DispatchQueue.global().async { [weak self] in
            guard let self else { return }
            self.stopBackend()   // SIGTERM + 1s + SIGKILL via shell, waits up to 4s

            // If port still in use → escalate: SIGKILL immediately (covers edge cases)
            if !self.pidsOnPort(self.backendPort).isEmpty {
                NSLog("VoiceFlow: Port still busy — escalating to hard kill")
                self.shellKillPort(self.backendPort, signal: "KILL")
                Thread.sleep(forTimeInterval: 1.0)
            }

            DispatchQueue.main.async {
                self.startBackend()
                self.waitForBackendReady { success in
                    DispatchQueue.main.async {
                        NSLog("VoiceFlow: Backend restart %@", success ? "succeeded" : "failed")
                        completion?(success)
                    }
                }
            }
        }
    }

    private func stopBackend() {
        if let process = backendProcess, process.isRunning {
            process.terminate()
        }
        backendProcess = nil
        // Also kill by port to catch externally started backends
        killExistingBackend()
        NSLog("VoiceFlow: Backend stopped")
    }

    private func findBackendPath() -> String {
        // Try relative path first (for development)
        let bundlePath = Bundle.main.bundlePath
        let devPath = URL(fileURLWithPath: bundlePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("backend")
            .path

        if FileManager.default.fileExists(atPath: "\(devPath)/src/voiceflow") {
            return devPath
        }

        // Fallback to hardcoded dev path
        let fallbackPath = NSString(string: "~/Developer/utils/voiceflow/backend").expandingTildeInPath
        return fallbackPath
    }

    private func findPythonPath() -> String? {
        let venvPython = "\(findBackendPath())/.venv/bin/python"
        if FileManager.default.fileExists(atPath: venvPython) {
            return venvPython
        }

        // Fallback to system Python 3.11
        let brewPython = "/opt/homebrew/bin/python3.11"
        if FileManager.default.fileExists(atPath: brewPython) {
            return brewPython
        }

        return "/usr/bin/python3"
    }

    // MARK: - Symbol Picker Helpers

    /// Seçilmeyen semboller için @pathKey referanslarını metinden kaldırır.
    static func applySymbolSelection(text: String, items: [SymbolItem]) -> String {
        var result = text
        for item in items where !item.selected {
            result = result.replacingOccurrences(of: "@\(item.pathKey)", with: "")
        }
        // Birden fazla boşluğu tek boşluğa indir
        while result.contains("  ") {
            result = result.replacingOccurrences(of: "  ", with: " ")
        }
        return result.trimmingCharacters(in: .whitespaces)
    }

    // MARK: - User Identity

    private func ensureUserID() {
        let key = AppSettings.userID
        if UserDefaults.standard.string(forKey: key)?.isEmpty ?? true {
            let newID = UUID().uuidString
            UserDefaults.standard.set(newID, forKey: key)
            NSLog("VoiceFlow: Generated user ID: %@", newID)
        }
    }

    // MARK: - Permissions

    private func requestAccessibilityPermission() {
        let options = [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true]
        let accessEnabled = AXIsProcessTrustedWithOptions(options as CFDictionary)

        if accessEnabled {
            NSLog("VoiceFlow: Accessibility permission GRANTED")
        } else {
            NSLog("VoiceFlow: Accessibility permission NOT granted - auto-paste will not work!")
            NSLog("VoiceFlow: Go to System Settings > Privacy & Security > Accessibility > Enable VoiceFlow")
        }
    }
}
