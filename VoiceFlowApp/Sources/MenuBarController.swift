import AppKit
import SwiftUI

// MARK: - MenuBarController
// Responsibility: NSStatusItem + NSMenu setup and updates.
// All business logic is in AppViewModel.

@MainActor
class MenuBarController: NSObject {
    private var statusItem: NSStatusItem?
    private let viewModel: AppViewModel
    private var historyWindow: NSWindow?

    init(viewModel: AppViewModel) {
        self.viewModel = viewModel
        super.init()
        setupStatusItem()
        checkAccessibility()
        observeViewModel()
    }

    // MARK: - Status Item

    private func setupStatusItem() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        guard let button = statusItem?.button else { return }
        button.image = NSImage(systemSymbolName: "waveform", accessibilityDescription: "VoiceFlow")
        button.action = #selector(statusBarButtonClicked)
        button.target = self
        rebuildMenu()
    }

    // MARK: - ViewModel observation

    private func observeViewModel() {
        // Poll via a timer — lightweight for a menu bar app.
        // Replace with withObservationTracking if needed for complex UIs.
        Timer.scheduledTimer(withTimeInterval: 0.3, repeats: true) { [weak self] _ in
            self?.syncUI()
        }
    }

    private func syncUI() {
        guard let menu = statusItem?.menu else { return }

        // Status text
        menu.item(withTag: 100)?.title = viewModel.statusText

        // Last result
        if let result = viewModel.lastResult {
            let item = menu.item(withTag: 150)
            let wasCorrected = result.corrected ?? false
            item?.title = (wasCorrected ? "✓ LLM: " : "✗ Raw: ") + String(result.text.prefix(60))
            item?.isHidden = false
        }

        // Recording icon
        let button = statusItem?.button
        let recording = viewModel.isRecording
        button?.image = NSImage(systemSymbolName: recording ? "waveform.circle.fill" : "waveform",
                                accessibilityDescription: "VoiceFlow")
        button?.contentTintColor = recording ? .systemRed : nil
    }

    // MARK: - Menu construction

    private func rebuildMenu() {
        let menu = NSMenu()

        menu.addItem(disabled("VoiceFlow"))
        menu.addItem(.separator())
        menu.addItem(disabled("Ready", tag: 100))

        let resultItem = NSMenuItem(title: "", action: nil, keyEquivalent: "")
        resultItem.tag = 150
        resultItem.isEnabled = false
        resultItem.isHidden = true
        menu.addItem(resultItem)

        menu.addItem(.separator())
        menu.addItem(action("History...", sel: #selector(showHistory), key: "h", tag: 400))
        menu.addItem(.separator())

        menu.addItem(submenu("Language", items: LanguageMode.allCases.map { mode in
            let item = NSMenuItem(title: mode.rawValue, action: #selector(selectLanguage(_:)), keyEquivalent: "")
            item.target = self
            item.representedObject = mode
            item.state = mode == viewModel.currentLanguageMode ? .on : .off
            return item
        }, tag: 200))

        menu.addItem(submenu("Mode", items: AppMode.allCases.map { mode in
            let item = NSMenuItem(title: mode.displayName, action: #selector(selectMode(_:)), keyEquivalent: "")
            item.target = self
            item.representedObject = mode
            item.state = mode == viewModel.currentAppMode ? .on : .off
            return item
        }, tag: 210))

        let correctionItem = NSMenuItem(title: "Smart Correction", action: #selector(toggleCorrection), keyEquivalent: "")
        correctionItem.target = self
        correctionItem.tag = 250
        correctionItem.state = viewModel.isCorrectionEnabled ? .on : .off
        menu.addItem(correctionItem)

        menu.addItem(.separator())
        menu.addItem(action("Toggle Recording", sel: #selector(toggleRecording), key: "r"))
        menu.addItem(action("Force Stop",        sel: #selector(forceStop),       key: "s"))
        menu.addItem(action("Restart Backend",   sel: #selector(restartBackend),  key: "b"))
        menu.addItem(action("Hard Reset Backend",sel: #selector(hardReset),       key: "k"))
        menu.addItem(.separator())
        menu.addItem(action("Settings...",       sel: #selector(openSettings),    key: ","))
        menu.addItem(action("Quit",              sel: #selector(quit),            key: "q"))

        statusItem?.menu = menu
    }

    // MARK: - Actions

    @objc private func statusBarButtonClicked() {}

    @objc private func selectLanguage(_ sender: NSMenuItem) {
        guard let mode = sender.representedObject as? LanguageMode else { return }
        viewModel.selectLanguageMode(mode)
        updateSubmenuCheckmarks(tag: 200, selected: mode, type: LanguageMode.self)
    }

    @objc private func selectMode(_ sender: NSMenuItem) {
        guard let mode = sender.representedObject as? AppMode else { return }
        viewModel.selectAppMode(mode)
        updateSubmenuCheckmarks(tag: 210, selected: mode, type: AppMode.self)
    }

    @objc private func toggleCorrection() {
        viewModel.toggleCorrection()
        statusItem?.menu?.item(withTag: 250)?.state = viewModel.isCorrectionEnabled ? .on : .off
    }

    @objc private func toggleRecording() {
        if viewModel.isRecording {
            Task { await viewModel.stopAndTranscribe() }
        } else {
            viewModel.startRecording()
        }
    }

    @objc private func forceStop() { viewModel.forceStop() }

    @objc private func restartBackend() {
        viewModel.statusText = "Restarting backend..."
        guard let appDelegate = NSApp.delegate as? AppDelegate else { return }
        appDelegate.restartBackend { [weak self] success in
            self?.viewModel.statusText = success ? "Ready" : "Backend restart failed"
        }
    }

    @objc private func hardReset() {
        viewModel.statusText = "Hard resetting..."
        guard let appDelegate = NSApp.delegate as? AppDelegate else { return }
        appDelegate.hardResetBackend { [weak self] success in
            self?.viewModel.statusText = success ? "Ready" : "Hard reset failed"
        }
    }

    @objc private func openSettings() {
        NSApp.sendAction(Selector(("showSettingsWindow:")), to: nil, from: nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    @objc private func quit() { NSApplication.shared.terminate(nil) }

    // MARK: - History window

    @objc private func showHistory() {
        if let w = historyWindow, w.isVisible { w.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps: true); return }
        let window = NSPanel(contentRect: NSRect(x: 0, y: 0, width: 420, height: 480),
                             styleMask: [.titled, .closable, .resizable, .nonactivatingPanel],
                             backing: .buffered, defer: false)
        window.contentViewController = NSHostingController(rootView: HistoryView(viewModel: viewModel))
        window.title = "VoiceFlow History"
        window.isFloatingPanel = true
        window.level = .floating
        window.center()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        historyWindow = window
    }

    // MARK: - Accessibility

    private func checkAccessibility() {
        if !AXIsProcessTrusted() {
            viewModel.statusText = "⚠ Enable Accessibility!"
        }
    }

    // MARK: - Helpers

    private func disabled(_ title: String, tag: Int = 0) -> NSMenuItem {
        let item = NSMenuItem(title: title, action: nil, keyEquivalent: "")
        item.isEnabled = false
        item.tag = tag
        return item
    }

    private func action(_ title: String, sel: Selector, key: String, tag: Int = 0) -> NSMenuItem {
        let item = NSMenuItem(title: title, action: sel, keyEquivalent: key)
        item.target = self
        item.tag = tag
        return item
    }

    private func submenu(_ title: String, items: [NSMenuItem], tag: Int) -> NSMenuItem {
        let parent = NSMenuItem(title: title, action: nil, keyEquivalent: "")
        parent.tag = tag
        let sub = NSMenu()
        items.forEach { sub.addItem($0) }
        parent.submenu = sub
        return parent
    }

    private func updateSubmenuCheckmarks<T: Equatable>(tag: Int, selected: T, type: T.Type) {
        guard let sub = statusItem?.menu?.item(withTag: tag)?.submenu else { return }
        for item in sub.items {
            item.state = (item.representedObject as? T) == selected ? .on : .off
        }
    }
}
