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

struct HistoryEntry: Identifiable {
    let id = UUID()
    let timestamp: Date
    let result: TranscriptionResult
}

class HistoryStore: ObservableObject {
    @Published var entries: [HistoryEntry] = []
    private let maxCount = 50

    func add(_ result: TranscriptionResult) {
        let entry = HistoryEntry(timestamp: Date(), result: result)
        entries.insert(entry, at: 0)
        if entries.count > maxCount {
            entries = Array(entries.prefix(maxCount))
        }
    }

    func clear() {
        entries.removeAll()
    }
}

// MARK: - History SwiftUI View

struct HistoryView: View {
    @ObservedObject var store: HistoryStore
    @State private var copiedId: UUID?

    private let timeFormatter: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "HH:mm:ss"
        return f
    }()

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Transcription History")
                    .font(.headline)
                Spacer()
                if !store.entries.isEmpty {
                    Button("Clear All") {
                        store.clear()
                    }
                    .buttonStyle(.plain)
                    .foregroundColor(.red)
                    .font(.caption)
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)

            Divider()

            if store.entries.isEmpty {
                Spacer()
                Text("No transcriptions yet")
                    .foregroundColor(.secondary)
                    .font(.subheadline)
                Spacer()
            } else {
                ScrollView {
                    LazyVStack(spacing: 0) {
                        ForEach(store.entries) { entry in
                            HistoryRow(
                                entry: entry,
                                isCopied: copiedId == entry.id,
                                timeFormatter: timeFormatter,
                                onCopy: { text in
                                    NSPasteboard.general.clearContents()
                                    NSPasteboard.general.setString(text, forType: .string)
                                    copiedId = entry.id
                                    DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
                                        if copiedId == entry.id {
                                            copiedId = nil
                                        }
                                    }
                                }
                            )
                            Divider().padding(.leading, 16)
                        }
                    }
                }
            }
        }
        .frame(width: 420, height: 480)
    }
}

struct HistoryRow: View {
    let entry: HistoryEntry
    let isCopied: Bool
    let timeFormatter: DateFormatter
    let onCopy: (String) -> Void

    private var wasCorrected: Bool {
        entry.result.corrected ?? false
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            // Top line: badge + time
            HStack(spacing: 6) {
                Text(wasCorrected ? "LLM" : "Raw")
                    .font(.system(size: 10, weight: .semibold))
                    .foregroundColor(.white)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(wasCorrected ? Color.green : Color.orange)
                    .cornerRadius(4)

                Text(timeFormatter.string(from: entry.timestamp))
                    .font(.caption)
                    .foregroundColor(.secondary)

                Spacer()

                Button(action: { onCopy(entry.result.text) }) {
                    Text(isCopied ? "Copied!" : "Copy")
                        .font(.caption)
                        .foregroundColor(isCopied ? .green : .accentColor)
                }
                .buttonStyle(.plain)
            }

            // Main text
            Text(entry.result.text)
                .font(.system(size: 13))
                .lineLimit(3)
                .frame(maxWidth: .infinity, alignment: .leading)

            // Raw text if corrected
            if wasCorrected, let raw = entry.result.rawText, raw != entry.result.text {
                Text("Raw: \(raw)")
                    .font(.system(size: 11))
                    .foregroundColor(.secondary)
                    .lineLimit(2)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
        .contentShape(Rectangle())
        .onTapGesture { onCopy(entry.result.text) }
    }
}

// MARK: - MenuBarController

class MenuBarController: NSObject {
    private var statusItem: NSStatusItem?
    private var popover: NSPopover?
    private let backendService = BackendService()
    private let hotkeyManager = HotkeyManager()
    private let pasteService = PasteService()

    private var isRecording = false
    private var currentMode: LanguageMode = .turkish
    private var isCorrectionEnabled = false
    private var activeApp: NSRunningApplication?

    private let historyStore = HistoryStore()
    private var historyWindow: NSWindow?

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

        // History window button
        let historyItem = NSMenuItem(title: "History...", action: #selector(showHistory), keyEquivalent: "h")
        historyItem.target = self
        historyItem.tag = 400
        menu.addItem(historyItem)

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
                        self.historyStore.add(result)
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

    // MARK: - History Window

    @objc private func showHistory() {
        // If window exists, just bring to front
        if let window = historyWindow, window.isVisible {
            window.makeKeyAndOrderFront(nil)
            NSApp.activate(ignoringOtherApps: true)
            return
        }

        let historyView = HistoryView(store: historyStore)
        let hostingController = NSHostingController(rootView: historyView)

        let window = NSPanel(
            contentRect: NSRect(x: 0, y: 0, width: 420, height: 480),
            styleMask: [.titled, .closable, .resizable, .nonactivatingPanel],
            backing: .buffered,
            defer: false
        )
        window.contentViewController = hostingController
        window.title = "VoiceFlow History"
        window.isFloatingPanel = true
        window.level = .floating
        window.center()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)

        self.historyWindow = window
    }
}
