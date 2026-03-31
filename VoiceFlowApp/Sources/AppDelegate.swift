import AppKit
import SwiftUI

class AppDelegate: NSObject, NSApplicationDelegate {
    private var menuBarController: MenuBarController?
    private var recordingOverlay: RecordingOverlayWindow?
    private var backendProcess: Process?
    private let backendPort = 8765
    private var healthCheckTimer: Timer?
    private var onboardingWindow: NSWindow?
    private var loginWindow: NSPanel?

    // Shared app state — created once, injected into MenuBarController and SettingsView
    var viewModel: AppViewModel?

    func applicationDidFinishLaunching(_ notification: Notification) {
        ensureUserID()

        let vm = AppViewModel()
        vm.onRestartBackend = { [weak self] completion in self?.restartBackend(completion: completion) }
        vm.onHardReset = { [weak self] completion in self?.hardResetBackend(completion: completion) }
        let overlay = RecordingOverlayWindow()
        self.recordingOverlay = overlay
        vm.onShowRecordingOverlay = { DispatchQueue.main.async { overlay.orderFront(nil) } }
        vm.onHideRecordingOverlay = { DispatchQueue.main.async { overlay.orderOut(nil) } }
        self.viewModel = vm

        let mode = UserDefaults.standard.string(forKey: AppSettings.deploymentMode) ?? "local"

        if mode == "server" {
            NSLog("VoiceFlow: Server mode — skipping local backend startup")
            DispatchQueue.main.async {
                self.menuBarController = MenuBarController(viewModel: vm)
            }
        } else {
            killExistingBackend()
            startBackend()
            waitForBackendReady { [weak self] success in
                DispatchQueue.main.async {
                    NSLog("VoiceFlow: Backend %@", success ? "ready" : "may not be ready")
                    self?.menuBarController = MenuBarController(viewModel: vm)
                }
            }
        }

        requestAccessibilityPermission()

        let deployMode = UserDefaults.standard.string(forKey: AppSettings.deploymentMode) ?? "local"
        if deployMode == "server" {
            vm.checkLoginState()
            // Observe login state: show login panel when not logged in
            Task { @MainActor [weak self] in
                // Wait briefly for checkLoginState to complete
                try? await Task.sleep(nanoseconds: 300_000_000)
                if !vm.isLoggedIn {
                    self?.showLoginWindow(viewModel: vm)
                }
                // Watch for login success to close panel
                while !vm.isLoggedIn {
                    try? await Task.sleep(nanoseconds: 200_000_000)
                }
                self?.loginWindow?.close()
                self?.loginWindow = nil
                self?.showOnboardingIfNeeded()
            }
        } else {
            showOnboardingIfNeeded()
        }
    }

    private func showLoginWindow(viewModel: AppViewModel) {
        let hosting = NSHostingController(rootView: LoginView(viewModel: viewModel))
        let panel = NSPanel(
            contentRect: NSRect(x: 0, y: 0, width: 380, height: 320),
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
            contentRect: NSRect(x: 0, y: 0, width: 480, height: 360),
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
        stopBackend()
    }

    // MARK: - Backend Lifecycle

    /// Kill all processes on backendPort. SIGTERM first, SIGKILL if still alive after 1s.
    /// Blocks until port is confirmed free (max 3s).
    private func killExistingBackend() {
        let pids = pidsOnPort(backendPort)
        guard !pids.isEmpty else { return }

        for pid in pids {
            kill(pid, SIGTERM)
            NSLog("VoiceFlow: SIGTERM → pid %d", pid)
        }

        // Wait up to 1s for graceful exit, then SIGKILL
        Thread.sleep(forTimeInterval: 1.0)
        for pid in pids {
            if kill(pid, 0) == 0 {  // process still alive
                kill(pid, SIGKILL)
                NSLog("VoiceFlow: SIGKILL → pid %d (didn't exit after SIGTERM)", pid)
            }
        }

        // Wait until port is actually free (max 2s more)
        for _ in 0..<20 {
            if pidsOnPort(backendPort).isEmpty { break }
            Thread.sleep(forTimeInterval: 0.1)
        }
        NSLog("VoiceFlow: Port %d is %@", backendPort, pidsOnPort(backendPort).isEmpty ? "free" : "still in use!")
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
        if llmMode == "cloud" {
            env["LLM_BACKEND"] = "ollama"
            // Read LLM_ENDPOINT from .env file in project root
            let projectRoot = URL(fileURLWithPath: backendPath).deletingLastPathComponent().path
            let envFile = "\(projectRoot)/.env"
            if let contents = try? String(contentsOfFile: envFile, encoding: .utf8) {
                for line in contents.components(separatedBy: "\n") {
                    let parts = line.components(separatedBy: "=")
                    if parts.count >= 2 {
                        let key = parts[0].trimmingCharacters(in: .whitespaces)
                        let value = parts[1...].joined(separator: "=").trimmingCharacters(in: .whitespaces)
                        if ["LLM_ENDPOINT", "LLM_MODEL", "HF_TOKEN"].contains(key) {
                            env[key] = value
                        }
                    }
                }
            }
            NSLog("VoiceFlow: LLM_BACKEND=ollama, LLM_ENDPOINT=%@", env["LLM_ENDPOINT"] ?? "nil")
        } else {
            env["LLM_BACKEND"] = "mlx"
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

    /// Public restart method — kills existing backend (including port squatters) and starts fresh.
    /// Runs blocking kill logic on a background thread to avoid freezing the UI.
    func restartBackend(completion: ((Bool) -> Void)? = nil) {
        NSLog("VoiceFlow: Restarting backend...")
        DispatchQueue.global().async { [weak self] in
            guard let self else { return }
            self.stopBackend()   // kills own process + any port squatter (blocks up to 3s)
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
