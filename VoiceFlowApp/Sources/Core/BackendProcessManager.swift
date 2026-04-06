import Foundation

/// Manages the backend Python process lifecycle: start, stop, restart, health check.
/// Extracted from AppDelegate to keep it focused on app lifecycle + wiring.
final class BackendProcessManager {
    private var process: Process?
    private var healthCheckTimer: Timer?
    private let port: Int

    init(port: Int = AppConstants.defaultLocalPort) {
        self.port = port
    }

    // MARK: - Public API

    /// Kill any existing backend on the port, then start a fresh process.
    func startFresh() {
        killExisting()
        start()
    }

    /// Wait for /health to return 200. Calls completion on main thread.
    func waitUntilReady(maxAttempts: Int = 30, completion: @escaping (Bool) -> Void) {
        var attempts = 0

        healthCheckTimer = Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { [weak self] timer in
            attempts += 1

            guard let self else {
                timer.invalidate()
                completion(false)
                return
            }

            if let proc = self.process, !proc.isRunning {
                timer.invalidate()
                NSLog("VoiceFlow: Backend process died")
                completion(false)
                return
            }

            self.checkHealth { isHealthy in
                if isHealthy {
                    timer.invalidate()
                    completion(true)
                } else if attempts >= maxAttempts {
                    timer.invalidate()
                    NSLog("VoiceFlow: Backend health check timed out after %d attempts", attempts)
                    completion(false)
                }
            }
        }
    }

    /// Soft restart: SIGTERM → wait → SIGKILL if needed → start fresh → wait for ready.
    func restart(completion: ((Bool) -> Void)? = nil) {
        NSLog("VoiceFlow: Restarting backend...")
        DispatchQueue.global().async { [weak self] in
            guard let self else { return }
            self.stop()

            if !self.pidsOnPort().isEmpty {
                NSLog("VoiceFlow: Port still busy — escalating to hard kill")
                self.shellKill(signal: "KILL")
                Thread.sleep(forTimeInterval: 1.0)
            }

            DispatchQueue.main.async {
                self.start()
                self.waitUntilReady { success in
                    DispatchQueue.main.async {
                        NSLog("VoiceFlow: Backend restart %@", success ? "succeeded" : "failed")
                        completion?(success)
                    }
                }
            }
        }
    }

    /// Hard reset: SIGKILL everything on port immediately, then restart.
    func hardReset(completion: @escaping (Bool) -> Void) {
        DispatchQueue.global().async { [weak self] in
            guard let self else { return }

            if let p = self.process, p.isRunning { p.terminate() }
            self.process = nil

            for pid in self.pidsOnPort() {
                kill(pid, SIGKILL)
                NSLog("VoiceFlow: Hard reset SIGKILL pid %d", pid)
            }
            self.waitForPortFree()

            NSLog("VoiceFlow: Hard reset — port %d %@", self.port,
                  self.pidsOnPort().isEmpty ? "free" : "still in use!")

            DispatchQueue.main.async {
                self.start()
                self.waitUntilReady { success in
                    DispatchQueue.main.async {
                        NSLog("VoiceFlow: Hard reset restart %@", success ? "succeeded" : "failed")
                        completion(success)
                    }
                }
            }
        }
    }

    /// Graceful stop: terminate process + kill by port.
    func stop() {
        if let proc = process, proc.isRunning {
            proc.terminate()
        }
        process = nil
        killExisting()
        NSLog("VoiceFlow: Backend stopped")
    }

    func invalidateHealthTimer() {
        healthCheckTimer?.invalidate()
    }

    // MARK: - Process Start

    private func start() {
        let backendPath = Self.findBackendPath()
        NSLog("VoiceFlow: Backend path: %@", backendPath)
        guard let pythonPath = Self.findPythonPath(backendPath: backendPath) else {
            NSLog("VoiceFlow: ERROR - Python not found!")
            return
        }
        NSLog("VoiceFlow: Python path: %@", pythonPath)

        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: pythonPath)
        proc.arguments = ["-m", "voiceflow.main"]
        proc.currentDirectoryURL = URL(fileURLWithPath: backendPath)
        proc.environment = Self.buildEnvironment(backendPath: backendPath)

        // Redirect stdout+stderr to log file
        let logPath = AppConstants.backendLogPath
        FileManager.default.createFile(atPath: logPath, contents: nil)
        if let logHandle = FileHandle(forWritingAtPath: logPath) {
            logHandle.seekToEndOfFile()
            proc.standardOutput = logHandle
            proc.standardError = logHandle
        }

        do {
            try proc.run()
            NSLog("VoiceFlow: Backend started with PID: %d", proc.processIdentifier)
        } catch {
            NSLog("VoiceFlow: Failed to start backend: %@", error.localizedDescription)
        }
        process = proc
    }

    // MARK: - Port Management

    private func killExisting() {
        shellKill(signal: "TERM")
        Thread.sleep(forTimeInterval: 1.0)

        if !pidsOnPort().isEmpty {
            shellKill(signal: "KILL")
            NSLog("VoiceFlow: SIGKILL sent to port %d", port)
        }

        waitForPortFree()
        NSLog("VoiceFlow: Port %d is %@", port, pidsOnPort().isEmpty ? "free" : "still in use!")
    }

    private func shellKill(signal: String) {
        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/bin/bash")
        task.arguments = ["-c", "lsof -nP -iTCP:\(port) -sTCP:LISTEN -t 2>/dev/null | xargs kill -\(signal) 2>/dev/null"]
        task.standardOutput = Pipe()
        task.standardError = Pipe()
        try? task.run()
        task.waitUntilExit()
    }

    private func pidsOnPort() -> [Int32] {
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

    private func waitForPortFree(maxWaitMs: Int = 3000) {
        let iterations = maxWaitMs / 100
        for _ in 0..<iterations {
            if pidsOnPort().isEmpty { break }
            Thread.sleep(forTimeInterval: 0.1)
        }
    }

    // MARK: - Health Check

    private func checkHealth(completion: @escaping (Bool) -> Void) {
        guard let url = URL(string: "\(AppConstants.defaultLocalURL)/health") else {
            completion(false)
            return
        }

        URLSession.shared.dataTask(with: url) { _, response, _ in
            let ok = (response as? HTTPURLResponse)?.statusCode == 200
            completion(ok)
        }.resume()
    }

    // MARK: - Path Discovery

    static func findBackendPath() -> String {
        // 1. Relative to bundle (works when running from DerivedData)
        let bundleRelative = URL(fileURLWithPath: Bundle.main.bundlePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("backend")
            .path
        if FileManager.default.fileExists(atPath: bundleRelative) {
            return bundleRelative
        }

        // 2. Known project path (works when app is in /Applications)
        let projectPath = AppConstants.projectBackendPath
        if FileManager.default.fileExists(atPath: projectPath) {
            return projectPath
        }

        NSLog("VoiceFlow: WARNING — backend path not found, using bundle-relative: %@", bundleRelative)
        return bundleRelative
    }

    static func findPythonPath(backendPath: String? = nil) -> String? {
        let backend = backendPath ?? findBackendPath()
        let venvPython = "\(backend)/.venv/bin/python"
        if FileManager.default.fileExists(atPath: venvPython) {
            return venvPython
        }

        let brewPython = "/opt/homebrew/bin/python3.11"
        if FileManager.default.fileExists(atPath: brewPython) {
            return brewPython
        }

        return "/usr/bin/python3"
    }

    // MARK: - Environment

    static func buildEnvironment(backendPath: String) -> [String: String] {
        var env = ProcessInfo.processInfo.environment
        let venvPath = "\(backendPath)/.venv"
        env["VIRTUAL_ENV"] = venvPath
        env["PATH"] = "\(venvPath)/bin:" + (env["PATH"] ?? "")
        env["PYTHONPATH"] = "\(backendPath)/src"
        env["HF_TOKEN"] = env["HF_TOKEN"] ?? ""

        let llmMode = LLMMode(rawValue: UserDefaults.standard.string(forKey: AppSettings.llmMode) ?? "") ?? .local

        // Parse .env file
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

        switch llmMode {
        case .cloud:
            env["LLM_BACKEND"] = "ollama"
            for key in ["LLM_ENDPOINT", "LLM_MODEL", "HF_TOKEN"] {
                if let val = dotEnv[key] { env[key] = val }
            }
            NSLog("VoiceFlow: LLM_BACKEND=ollama (RunPod), LLM_ENDPOINT=%@", env["LLM_ENDPOINT"] ?? "nil")

        case .alibaba:
            env["LLM_BACKEND"] = "ollama"
            env["LLM_ENDPOINT"] = AppConstants.alibabaDashScopeURL
            env["LLM_MODEL"] = AppConstants.alibabaScopeModel
            if let apiKey = dotEnv["ALIBABA_API_KEY"] { env["LLM_API_KEY"] = apiKey }
            NSLog("VoiceFlow: LLM_BACKEND=ollama (Alibaba DashScope), model=qwen-max")

        case .local:
            env["LLM_BACKEND"] = "mlx"
            if let adapterPath = dotEnv["LLM_ADAPTER_PATH"] {
                env["LLM_ADAPTER_PATH"] = adapterPath
                NSLog("VoiceFlow: LoRA adapter: %@", adapterPath)
            }
        }

        // Whisper IT model for engineering mode
        if let itModel = dotEnv["WHISPER_IT_MODEL"], !itModel.isEmpty {
            env["WHISPER_IT_MODEL"] = itModel
            NSLog("VoiceFlow: Whisper IT model: %@", itModel)
        }

        return env
    }
}
