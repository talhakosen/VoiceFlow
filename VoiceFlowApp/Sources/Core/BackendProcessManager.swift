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
        case portBusy(Int32)
        case lsofMissing([String])

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
            case let .portBusy(pid):
                return "Port \(AppConstants.defaultLocalPort) takılı bir süreç tarafından tutuluyor "
                     + "(PID \(pid)). Terminal'de: kill -9 \(pid)"
            case let .lsofMissing(tried):
                return "lsof bulunamadı (denenen: \(tried.joined(separator: ", "))) — "
                     + "port temizliği yapılamıyor"
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
    private var slowRetryTicks = 0
    private var isRestarting = false
    private let port: Int

    init(port: Int = AppConstants.defaultLocalPort) {
        self.port = port
    }

    // MARK: - Public API

    /// Kill any existing backend on the port, then start a fresh process.
    /// Port temizlenemezse başlatmaz — spawn etsek bind hatasıyla exit(1) verirdi.
    func startFresh() {
        guard killExisting() else { return }
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
            // stop() içindeki killExisting() TERM→KILL yükseltmesini zaten yapıyor.
            self.stop()

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

            let freed = self.killExisting()
            self.log("Hard reset — port \(self.port) \(freed ? "free" : "STILL IN USE")")

            DispatchQueue.main.async {
                self.autoRestartCount = 0   // manuel müdahale → watchdog kotasını sıfırla
                guard freed else {
                    // Port temizlenemediyse yeni süreç zaten exit(1) verecek.
                    // Boşuna spawn edip "process exited (1)" demektense sebebi söyle.
                    self.isRestarting = false
                    self.onStateChange?(false, self.lastFailure)
                    completion(false)
                    return
                }
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
                            self.slowRetryTicks = 0
                            self.lastFailure = nil
                            self.onStateChange?(true, nil)
                        }
                        return
                    }

                    // Hızlı seri tükendiyse pes etme, YAVAŞLA. Engel (dolu port,
                    // takılı süreç) kendiliğinden kalkabilir; eskiden limit
                    // dolunca watchdog bir daha hiç denemiyordu ve kullanıcı
                    // manuel müdahale etmeden sistem asla toparlamıyordu.
                    if self.autoRestartCount >= AppConstants.backendMaxAutoRestarts {
                        self.slowRetryTicks += 1
                        guard self.slowRetryTicks >= AppConstants.backendSlowRetryTicks else {
                            if self.lastFailure == nil {
                                self.lastFailure = .notHealthy
                                self.onStateChange?(false, .notHealthy)
                            }
                            return
                        }
                        self.slowRetryTicks = 0
                        self.log("Watchdog: slow retry (limit reached, still unhealthy)")
                        self.restart(completion: nil)
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

        // Son savunma: port doluyken spawn edersek uvicorn bind edemez ve
        // exit(1) verir — kullanıcı "process exited (1)" görür, sebebini değil.
        guard Self.isPortFree(port) else {
            let pid = pidsOnPort().first ?? -1
            lastFailure = .portBusy(pid)
            log("ERROR — \(lastFailure!.message)")
            process = nil
            return
        }

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
    //
    // Buradaki tek kural: "port boş" DİYE BİLMEK ile boş OLMASI aynı şey değil.
    // Eski kod `/usr/bin/lsof` çağırıyordu — bu makinede lsof `/usr/sbin/lsof`'ta.
    // Process.run() ENOENT fırlatıyor, catch bloğu boş dizi dönüyor, yönetici de
    // "Port free" yazıp SIGKILL aşamasını tamamen atlıyordu. Sonuç: takılı bir
    // backend portu 16 gün tuttu, her restart exit(1) verdi, "Zorla Yeniden
    // Başlat" hiçbir zaman SIGKILL göndermedi (2026-09-24).
    //
    // Artık: lsof adayları taranıyor, bulunamazsa AYRI bir hata olarak raporlanıyor,
    // ve nihai karar lsof'a değil bind() denemesine dayanıyor — uvicorn'un
    // çarpacağı şeyin aynısı.

    private static let lsofCandidates = ["/usr/sbin/lsof", "/usr/bin/lsof", "/opt/homebrew/bin/lsof"]

    private static let lsofPath: String? = lsofCandidates.first {
        FileManager.default.isExecutableFile(atPath: $0)
    }

    /// Port gerçekten bağlanabilir durumda mı? Ground truth — harici araç yok.
    /// uvicorn gibi SO_REUSEADDR ile deniyoruz ki aynı sonucu görelim.
    static func isPortFree(_ port: Int) -> Bool {
        let fd = socket(AF_INET, SOCK_STREAM, 0)
        guard fd >= 0 else { return true }   // karar veremiyoruz, engelleme
        defer { close(fd) }

        var yes: Int32 = 1
        setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &yes, socklen_t(MemoryLayout<Int32>.size))

        var addr = sockaddr_in()
        addr.sin_family = sa_family_t(AF_INET)
        addr.sin_port = UInt16(port).bigEndian
        addr.sin_addr.s_addr = inet_addr("127.0.0.1")

        let rc = withUnsafePointer(to: &addr) { ptr in
            ptr.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                Darwin.bind(fd, $0, socklen_t(MemoryLayout<sockaddr_in>.size))
            }
        }
        return rc == 0
    }

    /// TERM → bekle → KILL → bekle. Her aşamada bind() ile doğrular.
    /// Port temizlenemezse `lastFailure` set eder ve false döner.
    @discardableResult
    private func killExisting() -> Bool {
        if Self.isPortFree(port) {
            log("Port \(port) already free")
            return true
        }

        let pidsBefore = pidsOnPort()
        log("Port \(port) busy\(pidsBefore.isEmpty ? "" : " (PID \(pidsBefore.map(String.init).joined(separator: ", ")))") — terminating")

        signalPids(pidsBefore, sig: SIGTERM)
        if waitForPortFree(maxWaitMs: 3000) {
            log("Port \(port) freed by SIGTERM")
            return true
        }

        // Takılı uvicorn SIGTERM'i yutabiliyor (graceful shutdown MLX executor'da
        // asılı kalıyor). Eskiden bu aşamaya hiç gelinmiyordu.
        let pidsStill = pidsOnPort()
        log("SIGTERM insufficient — escalating to SIGKILL")
        signalPids(pidsStill, sig: SIGKILL)
        if waitForPortFree(maxWaitMs: 3000) {
            log("Port \(port) freed by SIGKILL")
            return true
        }

        if let pid = pidsOnPort().first {
            lastFailure = .portBusy(pid)
        } else if Self.lsofPath == nil {
            lastFailure = .lsofMissing(Self.lsofCandidates)
        } else {
            lastFailure = .portBusy(-1)
        }
        log("ERROR — \(lastFailure!.message)")
        return false
    }

    private func signalPids(_ pids: [Int32], sig: Int32) {
        guard !pids.isEmpty else {
            log("No PIDs resolved for port \(port) — cannot signal (lsof: \(Self.lsofPath ?? "MISSING"))")
            return
        }
        for pid in pids {
            let rc = kill(pid, sig)
            log("kill(\(pid), \(sig == SIGKILL ? "SIGKILL" : "SIGTERM")) → \(rc == 0 ? "ok" : "errno \(errno)")")
        }
    }

    private func pidsOnPort() -> [Int32] {
        guard let lsof = Self.lsofPath else {
            log("lsof not found in \(Self.lsofCandidates.joined(separator: ", "))")
            return []
        }

        let task = Process()
        task.executableURL = URL(fileURLWithPath: lsof)
        task.arguments = ["-nP", "-iTCP:\(port)", "-sTCP:LISTEN", "-t"]
        let pipe = Pipe()
        task.standardOutput = pipe
        task.standardError = Pipe()
        do {
            try task.run()
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            task.waitUntilExit()
            let output = String(data: data, encoding: .utf8) ?? ""
            return output.components(separatedBy: "\n").compactMap {
                Int32($0.trimmingCharacters(in: .whitespaces))
            }
        } catch {
            // Sessizce boş dönmek bu hatanın ta kendisiydi.
            log("ERROR — lsof at \(lsof) failed: \(error.localizedDescription)")
            return []
        }
    }

    /// Port serbest kalana kadar bekler. Serbest kaldıysa true.
    @discardableResult
    private func waitForPortFree(maxWaitMs: Int = 3000) -> Bool {
        let iterations = max(1, maxWaitMs / 100)
        for _ in 0..<iterations {
            if Self.isPortFree(port) { return true }
            Thread.sleep(forTimeInterval: 0.1)
        }
        return Self.isPortFree(port)
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
