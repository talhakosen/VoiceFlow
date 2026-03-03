import AppKit
import SwiftUI

class AppDelegate: NSObject, NSApplicationDelegate {
    private var menuBarController: MenuBarController?
    private var backendProcess: Process?
    private let backendPort = 8765
    private var healthCheckTimer: Timer?

    func applicationDidFinishLaunching(_ notification: Notification) {
        // Kill any existing backend on our port first
        killExistingBackend()

        // Start Python backend
        startBackend()

        // Wait for backend to be ready before setting up UI
        waitForBackendReady { [weak self] success in
            DispatchQueue.main.async {
                if success {
                    print("Backend is ready")
                } else {
                    print("Warning: Backend may not be ready")
                }
                // Setup menu bar regardless
                self?.menuBarController = MenuBarController()
            }
        }

        // Request accessibility permissions if needed
        requestAccessibilityPermission()
    }

    func applicationWillTerminate(_ notification: Notification) {
        healthCheckTimer?.invalidate()
        stopBackend()
    }

    // MARK: - Backend Lifecycle

    private func killExistingBackend() {
        // Kill any process using our port
        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/usr/bin/lsof")
        task.arguments = ["-ti", ":\(backendPort)"]

        let pipe = Pipe()
        task.standardOutput = pipe

        do {
            try task.run()
            task.waitUntilExit()

            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            if let output = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines),
               !output.isEmpty {
                // Kill each PID found
                for pidStr in output.components(separatedBy: "\n") {
                    if let pid = Int32(pidStr) {
                        kill(pid, SIGTERM)
                        print("Killed existing backend process: \(pid)")
                    }
                }
                // Give it time to die
                Thread.sleep(forTimeInterval: 0.5)
            }
        } catch {
            print("Could not check for existing backend: \(error)")
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

    private func stopBackend() {
        if let process = backendProcess, process.isRunning {
            process.terminate()
            // Wait a bit for graceful shutdown
            DispatchQueue.global().asyncAfter(deadline: .now() + 1) {
                if process.isRunning {
                    process.interrupt() // Force kill if still running
                }
            }
        }
        backendProcess = nil
        print("Backend stopped")
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
