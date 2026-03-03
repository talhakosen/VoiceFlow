import AppKit
import SwiftUI

enum LanguageMode: String, CaseIterable {
    case auto = "Auto Detect"
    case turkish = "Türkçe"
    case english = "English"
    case translateToEnglish = "Any → English"

    var language: String? {
        switch self {
        case .auto: return nil
        case .turkish: return "tr"
        case .english: return "en"
        case .translateToEnglish: return nil
        }
    }

    var task: String {
        switch self {
        case .translateToEnglish: return "translate"
        default: return "transcribe"
        }
    }
}

class MenuBarController: NSObject {
    private var statusItem: NSStatusItem?
    private var popover: NSPopover?
    private let backendService = BackendService()
    private let hotkeyManager = HotkeyManager()
    private let pasteService = PasteService()

    private var isRecording = false
    private var currentMode: LanguageMode = .auto
    private var isCorrectionEnabled = true
    private var activeApp: NSRunningApplication?

    override init() {
        super.init()
        setupStatusItem()
        setupHotkey()
        checkAccessibility()
    }

    // MARK: - Status Item

    private func setupStatusItem() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)

        if let button = statusItem?.button {
            button.image = NSImage(systemSymbolName: "waveform", accessibilityDescription: "VoiceFlow")
            button.action = #selector(togglePopover)
            button.target = self
        }

        setupMenu()
    }

    private func setupMenu() {
        let menu = NSMenu()

        let titleItem = NSMenuItem(title: "VoiceFlow", action: nil, keyEquivalent: "")
        titleItem.isEnabled = false
        menu.addItem(titleItem)
        menu.addItem(NSMenuItem.separator())

        let statusMenuItem = NSMenuItem(title: "Ready", action: nil, keyEquivalent: "")
        statusMenuItem.tag = 100
        statusMenuItem.isEnabled = false
        menu.addItem(statusMenuItem)

        let lastResultItem = NSMenuItem(title: "", action: nil, keyEquivalent: "")
        lastResultItem.tag = 150
        lastResultItem.isEnabled = false
        lastResultItem.isHidden = true
        menu.addItem(lastResultItem)

        menu.addItem(NSMenuItem.separator())

        // Language mode submenu
        let languageMenu = NSMenu()
        for mode in LanguageMode.allCases {
            let item = NSMenuItem(title: mode.rawValue, action: #selector(selectLanguageMode(_:)), keyEquivalent: "")
            item.target = self
            item.representedObject = mode
            if mode == currentMode {
                item.state = .on
            }
            languageMenu.addItem(item)
        }

        let languageMenuItem = NSMenuItem(title: "Language", action: nil, keyEquivalent: "")
        languageMenuItem.submenu = languageMenu
        languageMenuItem.tag = 200
        menu.addItem(languageMenuItem)

        // Smart Correction toggle
        let correctionItem = NSMenuItem(title: "Smart Correction", action: #selector(toggleCorrection(_:)), keyEquivalent: "")
        correctionItem.target = self
        correctionItem.tag = 250
        correctionItem.state = isCorrectionEnabled ? .on : .off
        menu.addItem(correctionItem)

        menu.addItem(NSMenuItem.separator())

        let toggleItem = NSMenuItem(title: "Toggle Recording", action: #selector(toggleRecordingFromMenu), keyEquivalent: "r")
        toggleItem.target = self
        toggleItem.tag = 300
        menu.addItem(toggleItem)

        let forceStopItem = NSMenuItem(title: "Force Stop", action: #selector(forceStopFromMenu), keyEquivalent: "s")
        forceStopItem.target = self
        forceStopItem.tag = 310
        menu.addItem(forceStopItem)

        menu.addItem(NSMenuItem.separator())

        let quitItem = NSMenuItem(title: "Quit", action: #selector(quit), keyEquivalent: "q")
        quitItem.target = self
        menu.addItem(quitItem)

        self.statusItem?.menu = menu
    }

    @objc private func selectLanguageMode(_ sender: NSMenuItem) {
        guard let mode = sender.representedObject as? LanguageMode else { return }
        currentMode = mode

        // Update checkmarks
        if let menu = statusItem?.menu,
           let languageMenuItem = menu.item(withTag: 200),
           let submenu = languageMenuItem.submenu {
            for item in submenu.items {
                item.state = (item.representedObject as? LanguageMode) == mode ? .on : .off
            }
        }

        // Update backend config
        Task {
            try? await backendService.updateConfig(language: mode.language, task: mode.task)
        }

        print("Language mode changed to: \(mode.rawValue)")
    }

    @objc private func toggleCorrection(_ sender: NSMenuItem) {
        isCorrectionEnabled.toggle()
        sender.state = isCorrectionEnabled ? .on : .off

        Task {
            try? await backendService.updateConfig(
                language: currentMode.language,
                task: currentMode.task,
                correctionEnabled: isCorrectionEnabled
            )
        }

        print("Smart Correction: \(isCorrectionEnabled ? "ON" : "OFF")")
    }

    @objc private func togglePopover() {
        // For now, just show menu
    }

    @objc private func toggleRecordingFromMenu() {
        toggleRecording()
    }

    @objc private func forceStopFromMenu() {
        NSLog("VoiceFlow: Force stop from menu")
        isRecording = false
        hotkeyManager.resetState()
        updateStatusIcon(recording: false)
        updateStatusText("Stopping...")

        Task {
            _ = try? await backendService.stopRecording()
            await MainActor.run {
                updateStatusText("Ready")
            }
        }
    }

    @objc private func quit() {
        NSApplication.shared.terminate(nil)
    }

    // MARK: - Accessibility Check

    private func checkAccessibility() {
        if !AXIsProcessTrusted() {
            updateStatusText("⚠ Enable Accessibility!")
            NSLog("VoiceFlow: Accessibility NOT granted - paste will fail")
        }
    }

    // MARK: - Hotkey

    private func setupHotkey() {
        hotkeyManager.onStartRecording = { [weak self] in
            self?.startRecording()
        }

        hotkeyManager.onStopRecording = { [weak self] in
            self?.stopRecordingAndTranscribe()
        }

        hotkeyManager.start()
    }

    // MARK: - Recording

    private func toggleRecording() {
        if isRecording {
            stopRecordingAndTranscribe()
        } else {
            startRecording()
        }
    }

    private func startRecording() {
        guard !isRecording else { return }
        isRecording = true

        updateStatusIcon(recording: true)

        // Remember which app was active so we can paste there later
        activeApp = NSWorkspace.shared.frontmostApplication
        NSLog("VoiceFlow: Starting recording (active app: %@ pid:%d, accessibility: %@)",
              activeApp?.localizedName ?? "none",
              activeApp?.processIdentifier ?? 0,
              pasteService.hasAccessibility ? "YES" : "NO")

        Task {
            do {
                try await backendService.startRecording()
                NSLog("VoiceFlow: Recording started successfully")
            } catch {
                NSLog("VoiceFlow: Failed to start recording: \(error)")
                await MainActor.run {
                    isRecording = false
                    updateStatusIcon(recording: false)
                }
            }
        }
    }

    private func stopRecordingAndTranscribe() {
        guard isRecording else { return }
        isRecording = false

        updateStatusIcon(recording: false)
        updateStatusText(isCorrectionEnabled ? "Transcribing + Correcting..." : "Transcribing...")
        NSLog("VoiceFlow: Stopping recording, sending to backend...")

        let savedApp = activeApp

        Task {
            do {
                let result = try await backendService.stopRecording()
                let wasCorrected = result.corrected ?? false
                NSLog("VoiceFlow: Result: '%@' (corrected: %@, lang: %@, dur: %.1fs)",
                      result.text,
                      wasCorrected ? "YES" : "NO",
                      result.language ?? "?",
                      result.duration ?? 0)
                if wasCorrected, let raw = result.rawText {
                    NSLog("VoiceFlow: Raw: '%@'", raw)
                }

                if !result.text.isEmpty {
                    await MainActor.run {
                        self.updateLastResult(result)
                        if let app = savedApp {
                            NSLog("VoiceFlow: Re-activating: %@ (pid %d)",
                                  app.localizedName ?? "?", app.processIdentifier)
                            app.activate(options: .activateIgnoringOtherApps)
                        } else {
                            NSLog("VoiceFlow: WARNING - no saved activeApp")
                        }
                        DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) { [weak self] in
                            NSLog("VoiceFlow: Pasting text now...")
                            self?.pasteService.pasteText(result.text)
                            self?.updateStatusText("Ready")
                        }
                    }
                } else {
                    NSLog("VoiceFlow: Empty transcription result")
                    await MainActor.run {
                        updateStatusText("Ready")
                    }
                }
            } catch {
                NSLog("VoiceFlow: Failed to stop/transcribe: \(error)")
                await MainActor.run {
                    updateStatusText("Ready")
                }
            }
        }
    }

    private func updateStatusIcon(recording: Bool) {
        DispatchQueue.main.async { [weak self] in
            if let button = self?.statusItem?.button {
                let symbolName = recording ? "waveform.circle.fill" : "waveform"
                button.image = NSImage(systemSymbolName: symbolName, accessibilityDescription: "VoiceFlow")
                button.contentTintColor = recording ? .systemRed : nil
            }

            self?.updateStatusText(recording ? "Recording... (Fn×2 to stop)" : "Ready")
        }
    }

    private func updateStatusText(_ text: String) {
        if let menu = statusItem?.menu,
           let statusItem = menu.item(withTag: 100) {
            statusItem.title = text
        }
    }

    private func updateLastResult(_ result: TranscriptionResult) {
        guard let menu = statusItem?.menu,
              let item = menu.item(withTag: 150) else { return }

        let wasCorrected = result.corrected ?? false
        let prefix = wasCorrected ? "✓ LLM: " : "✗ Raw: "
        let displayText = String(result.text.prefix(60))
        item.title = prefix + displayText
        item.isHidden = false

        if wasCorrected, let raw = result.rawText {
            item.toolTip = "Raw: \(raw)"
        } else {
            item.toolTip = nil
        }
    }
}
