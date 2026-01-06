import AppKit
import SwiftUI

class AppDelegate: NSObject, NSApplicationDelegate {
    private var menuBarController: MenuBarController?
    private var backendProcess: Process?

    func applicationDidFinishLaunching(_ notification: Notification) {
        // Start Python backend
        startBackend()

        // Setup menu bar
        menuBarController = MenuBarController()

        // Request accessibility permissions if needed
        requestAccessibilityPermission()
    }

    func applicationWillTerminate(_ notification: Notification) {
        stopBackend()
    }

    // MARK: - Backend Lifecycle

    private func startBackend() {
        let backendPath = findBackendPath()
        guard let pythonPath = findPythonPath() else {
            print("Python not found")
            return
        }

        backendProcess = Process()
        backendProcess?.executableURL = URL(fileURLWithPath: pythonPath)
        backendProcess?.arguments = ["-m", "voiceflow.main"]
        backendProcess?.currentDirectoryURL = URL(fileURLWithPath: backendPath)

        // Set up environment for venv
        var env = ProcessInfo.processInfo.environment
        let venvPath = "\(backendPath)/.venv"
        env["VIRTUAL_ENV"] = venvPath
        env["PATH"] = "\(venvPath)/bin:" + (env["PATH"] ?? "")
        backendProcess?.environment = env

        do {
            try backendProcess?.run()
            print("Backend started with PID: \(backendProcess?.processIdentifier ?? 0)")
        } catch {
            print("Failed to start backend: \(error)")
        }
    }

    private func stopBackend() {
        backendProcess?.terminate()
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

        if !accessEnabled {
            print("Accessibility permission required for global hotkeys")
        }
    }
}
