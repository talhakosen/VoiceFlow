import Foundation

/// Manages the backend Python process lifecycle: start, stop, restart, health check.
/// Extracted from AppDelegate to keep it focused on app lifecycle + wiring.
///
/// Tasarım notları (stale-state önlemleri):
/// - Path DOĞRULANIR (`src/voiceflow/main.py` marker). Yanlış dizine `Process.run()`
///   atmak sessizce fırlatır ve backend hiç ayağa kalkmaz — proje taşındığında yaşandı.
/// - Log dosyası her start'ta SİLİNMEZ; append edilir. Aksi halde çöken backend'in
///   kanıtı bir sonraki restart'ta yok oluyor.
/// - Watchdog: backend ölürse otomatik yeniden başlatılır ve durum dışarı bildirilir.
final class BackendProcessManager {

    /// Tek örnek — hem AppDelegate hem BackendProcessClient (TCA) aynı süreci yönetmeli.
    static let shared = BackendProcessManager()

    // MARK: - Observable failure state

    enum Failure: Equatable {
        case backendPathNotFound([String])
        case pythonNotFound(String)
        case spawnFailed(String)
        case notHealthy

        var message: String {
            switch self {
            case let .backendPathNotFound(tried):
                return "Backend klasörü bulunamadı (denenen: \(tried.joined(separator: ", ")))"
            case let .pythonNotFound(path):
                return "Python bulunamadı: \(path)"
            case let .spawnFailed(err):
                return "Servis başlatılamadı: \(err)"
            case .notHealthy:
                return "Servis yanıt vermiyor"
            }
        }
    }

    private(set) var lastFailure: Failure?
    /// Watchdog / restart sonucu değiştiğinde tetiklenir (main thread).
    var onStateChange: ((Bool, Failure?) -> Void)?

    private var process: Process?
    private var healthCheckTimer: Timer?
    private var watchdogTimer: Timer?
    private var autoRestartCount = 0
    private var isRestarting = false
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
        healthCheckTimer?.invalidate()

        healthCheckTimer = Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { [weak self] timer in
            attempts += 1

            guard let self else {
                timer.invalidate()
                completion(false)
                return
            }

            // Süreç hiç doğmadıysa (spawn hatası) beklemeye gerek yok.
            if self.process == nil {
                timer.invalidate()
                self.log("Backend process was never spawned — \(self.lastFailure?.message ?? "unknown")")
                completion(false)
                return
            }

            if let proc = self.process, !proc.isRunning {
                timer.invalidate()
                self.log("Backend process died (exit \(proc.terminationStatus)) — see \(AppConstants.backendLogPath)")
                self.lastFailure = .spawnFailed("process exited (\(proc.terminationStatus))")
                completion(false)
                return
            }

            self.checkHealth { isHealthy in
                if isHealthy {
                    timer.invalidate()
                    self.lastFailure = nil
                    completion(true)
                } else if attempts >= maxAttempts {
                    timer.invalidate()
                    self.log("Backend health check timed out after \(attempts) attempts")
                    self.lastFailure = .notHealthy
                    completion(false)
                }
            }
        }
    }

    /// Soft restart: SIGTERM → wait → SIGKILL if needed → start fresh → wait for ready.
    func restart(completion: ((Bool) -> Void)? = nil) {
        guard !isRestarting else {
            log("restart() ignored — already restarting")
            completion?(false)
            return
        }
        isRestarting = true
        log("Restarting backend...")
        DispatchQueue.global().async { [weak self] in
            guard let self else { return }
            self.stop()

            if !self.pidsOnPort().isEmpty {
                self.log("Port still busy — escalating to hard kill")
                self.shellKill(signal: "KILL")
                Thread.sleep(forTimeInterval: 1.0)
            }

            DispatchQueue.main.async {
                self.start()
                self.waitUntilReady { success in
                    DispatchQueue.main.async {
                        self.isRestarting = false
                        self.log("Backend restart \(success ? "succeeded" : "failed")")
                        self.onStateChange?(success, success ? nil : self.lastFailure)
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
            self.isRestarting = true

            if let p = self.process, p.isRunning { p.terminate() }
            self.process = nil

            for pid in self.pidsOnPort() {
                kill(pid, SIGKILL)
                self.log("Hard reset SIGKILL pid \(pid)")
            }
            self.waitForPortFree()

            self.log("Hard reset — port \(self.port) \(self.pidsOnPort().isEmpty ? "free" : "still in use!")")

            DispatchQueue.main.async {
                self.autoRestartCount = 0   // manuel müdahale → watchdog kotasını sıfırla
                self.start()
                self.waitUntilReady { success in
                    DispatchQueue.main.async {
                        self.isRestarting = false
                        self.log("Hard reset restart \(success ? "succeeded" : "failed")")
                        self.onStateChange?(success, success ? nil : self.lastFailure)
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
        log("Backend stopped")
    }

    func invalidateHealthTimer() {
        healthCheckTimer?.invalidate()
        healthCheckTimer = nil
    }

    // MARK: - Watchdog

    /// Periyodik sağlık kontrolü. Backend ölürse otomatik toparlar.
    /// Sonsuz restart döngüsünü önlemek için `backendMaxAutoRestarts` limiti var:
    /// limit aşılınca kullanıcıya "Zorla Yeniden Başlat" için hata bildirilir.
    func startWatchdog() {
        watchdogTimer?.invalidate()
        watchdogTimer = Timer.scheduledTimer(
            withTimeInterval: AppConstants.backendWatchdogInterval,
            repeats: true
        ) { [weak self] _ in
            guard let self, !self.isRestarting else { return }

            self.checkHealth { healthy in
                DispatchQueue.main.async {
                    if healthy {
                        if self.autoRestartCount > 0 || self.lastFailure != nil {
                            self.autoRestartCount = 0
                            self.lastFailure = nil
                            self.onStateChange?(true, nil)
                        }
                        return
                    }

                    guard self.autoRestartCount < AppConstants.backendMaxAutoRestarts else {
                        if self.lastFailure == nil {
                            self.lastFailure = .notHealthy
                            self.onStateChange?(false, .notHealthy)
                        }
                        return
                    }

                    self.autoRestartCount += 1
                    self.log("Watchdog: backend unhealthy — auto-restart \(self.autoRestartCount)/\(AppConstants.backendMaxAutoRestarts)")
                    self.restart(completion: nil)
                }
            }
        }
    }

    func stopWatchdog() {
        watchdogTimer?.invalidate()
        watchdogTimer = nil
    }

    /// Anlık durum — UI/menü için.
    func isHealthy(completion: @escaping (Bool) -> Void) {
        checkHealth(completion: completion)
    }

    // MARK: - Process Start

    private func start() {
        guard let backendPath = Self.findBackendPath() else {
            lastFailure = .backendPathNotFound(Self.searchedBackendPaths())
            log("ERROR — \(lastFailure!.message)")
            process = nil
            return
        }
        log("Backend path: \(backendPath)")

        guard let pythonPath = Self.findPythonPath(backendPath: backendPath),
              FileManager.default.isExecutableFile(atPath: pythonPath) else {
            lastFailure = .pythonNotFound("\(backendPath)/.venv/bin/python")
            log("ERROR — \(lastFailure!.message)")
            process = nil
            return
        }
        log("Python path: \(pythonPath)")

        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: pythonPath)
        proc.arguments = ["-m", "voiceflow.main"]
        proc.currentDirectoryURL = URL(fileURLWithPath: backendPath)
        proc.environment = Self.buildEnvironment(backendPath: backendPath)

        // Redirect stdout+stderr to log file — APPEND, asla truncate etme.
        // Truncate edersek çöken backend'in stack trace'i bir sonraki restart'ta kaybolur.
        let logPath = AppConstants.backendLogPath
        if !FileManager.default.fileExists(atPath: logPath) {
            FileManager.default.createFile(atPath: logPath, contents: nil)
        }
        if let logHandle = FileHandle(forWritingAtPath: logPath) {
            logHandle.seekToEndOfFile()
            let banner = "\n===== VoiceFlow backend start \(ISO8601DateFormatter().string(from: Date())) — cwd=\(backendPath) =====\n"
            logHandle.write(Data(banner.utf8))
            proc.standardOutput = logHandle
            proc.standardError = logHandle
        }

        proc.terminationHandler = { [weak self] p in
            self?.log("Backend exited with status \(p.terminationStatus) (reason: \(p.terminationReason.rawValue))")
        }

        do {
            try proc.run()
            lastFailure = nil
            process = proc
            log("Backend started with PID: \(proc.processIdentifier)")
        } catch {
            lastFailure = .spawnFailed(error.localizedDescription)
            process = nil   // spawn olmadıysa ölü Process nesnesini tutma
            log("Failed to start backend: \(error.localizedDescription)")
        }
    }

    // MARK: - Port Management

    private func killExisting() {
        shellKill(signal: "TERM")
        Thread.sleep(forTimeInterval: 1.0)

        if !pidsOnPort().isEmpty {
            shellKill(signal: "KILL")
            log("SIGKILL sent to port \(port)")
        }

        waitForPortFree()
        log("Port \(port) is \(pidsOnPort().isEmpty ? "free" : "still in use!")")
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

        var request = URLRequest(url: url)
        request.timeoutInterval = AppConstants.healthCheckTimeout
        URLSession.shared.dataTask(with: request) { _, response, _ in
            let ok = (response as? HTTPURLResponse)?.statusCode == 200
            completion(ok)
        }.resume()
    }

    // MARK: - Path Discovery

    /// Denenen tüm adaylar — hata mesajında göstermek için.
    static func searchedBackendPaths() -> [String] {
        var paths: [String] = []
        if let override = UserDefaults.standard.string(forKey: AppConstants.backendPathOverrideKey),
           !override.isEmpty {
            paths.append(override)
        }
        paths.append(bundleRelativeBackendPath())
        paths.append(contentsOf: AppConstants.backendPathCandidates)
        return paths
    }

    private static func bundleRelativeBackendPath() -> String {
        URL(fileURLWithPath: Bundle.main.bundlePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("backend")
            .path
    }

    /// Marker dosyası (`src/voiceflow/main.py`) olan İLK adayı döner.
    /// Sadece klasör varlığına bakmak yetmez: /Applications/backend gibi
    /// var olmayan/yanlış bir dizin `Process.run()`'ı sessizce patlatıyordu.
    static func findBackendPath() -> String? {
        for candidate in searchedBackendPaths() where isValidBackendPath(candidate) {
            return candidate
        }
        return nil
    }

    static func isValidBackendPath(_ path: String) -> Bool {
        FileManager.default.fileExists(atPath: "\(path)/\(AppConstants.backendMarkerFile)")
    }

    static func findPythonPath(backendPath: String? = nil) -> String? {
        guard let backend = backendPath ?? findBackendPath() else { return nil }
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
        case .runpod:
            env["WHISPER_BACKEND"] = "runpod"
            for key in ["RUNPOD_INFERENCE_URL", "RUNPOD_API_TOKEN", "RUNPOD_ENDPOINT_ID", "HF_TOKEN"] {
                if let val = dotEnv[key] { env[key] = val }
            }
            NSLog("VoiceFlow: WHISPER_BACKEND=runpod, URL=%@", env["RUNPOD_INFERENCE_URL"] ?? "nil")

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

    // MARK: - Logging

    /// NSLog + dosya. Unified log'da NSLog kaybolabiliyor (private data),
    /// bu yüzden teşhis için ayrıca /tmp/voiceflow-swift.log'a yazıyoruz.
    private func log(_ msg: String) {
        NSLog("VoiceFlow: %@", msg)
        let line = "\(ISO8601DateFormatter().string(from: Date())) [BackendProcessManager] \(msg)\n"
        guard let data = line.data(using: .utf8) else { return }
        let path = AppConstants.swiftLogPath
        if let fh = FileHandle(forWritingAtPath: path) {
            fh.seekToEndOfFile(); fh.write(data); fh.closeFile()
        } else {
            try? data.write(to: URL(fileURLWithPath: path))
        }
    }
}
