import AppKit
import SwiftUI

// MARK: - MenuBarController
// Responsibility: NSStatusItem + NSMenu setup and updates.
// All business logic is in AppViewModel.

@MainActor
class MenuBarController: NSObject, NSMenuDelegate {
    private var statusItem: NSStatusItem?
    private let viewModel: AppViewModel
    private var settingsWindow: NSWindow?
    private var itDatasetWindowController = ITDatasetWindowController()
    private var lastKnownRole: String = ""

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
            Task { @MainActor [weak self] in self?.syncUI() }
        }
    }

    private func syncUI() {
        guard let menu = statusItem?.menu else { return }

        // Rebuild menu if role changed (e.g. after login)
        let currentRole = viewModel.currentUser?.role ?? ""
        if currentRole != lastKnownRole {
            lastKnownRole = currentRole
            rebuildMenu()
            return
        }

        // Status text (bottom) — version sol, status sağa yapışık
        let v = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? ""
        let b = Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? ""
        if let item = menu.item(withTag: 100) {
            item.attributedTitle = makeVersionStatusAttr(version: v, build: b, status: viewModel.statusText)
        }

        // Mode checkmarks
        for item in menu.items {
            if let raw = item.representedObject as? String,
               let mode = AppMode(rawValue: raw) {
                item.state = viewModel.currentAppMode == mode ? .on : .off
            }
        }

        // Recording toggle title + icon
        let recording = viewModel.isRecording
        if let recItem = menu.item(withTag: 101) {
            recItem.title = recording ? "Kaydı Durdur" : "Kaydı Başlat"
            if let img = NSImage(systemSymbolName: recording ? "stop.circle" : "mic",
                                  accessibilityDescription: nil) {
                img.isTemplate = true
                recItem.image = img
            }
        }

        // Status bar icon
        let button = statusItem?.button
        button?.image = NSImage(systemSymbolName: recording ? "waveform.circle.fill" : "waveform",
                                accessibilityDescription: "VoiceFlow")
        button?.contentTintColor = recording ? .systemRed : nil
    }

    // MARK: - Menu construction

    private func rebuildMenu() {
        let menu = NSMenu()

        let isRec = viewModel.isRecording
        menu.addItem(action(isRec ? "Kaydı Durdur" : "Kaydı Başlat",
                            sel: #selector(toggleRecording),
                            key: "", icon: isRec ? "stop.circle" : "mic", tag: 101))
        // Mode switcher
        menu.addItem(.separator())
        for mode in AppMode.allCases {
            let item = action(mode.displayName, sel: #selector(switchMode(_:)),
                              key: mode.menuKeyEquivalent, icon: mode.menuIcon)
            item.keyEquivalentModifierMask = [.option]
            item.state = viewModel.currentAppMode == mode ? .on : .off
            item.representedObject = mode.rawValue
            menu.addItem(item)
        }
        menu.addItem(.separator())

        menu.addItem(action("Servisi Yeniden Başlat", sel: #selector(restartService),
                            key: "", icon: "arrow.clockwise"))
        menu.addItem(action("Ses Eğitimi...",         sel: #selector(openITDataset),
                            key: "", icon: "waveform.badge.microphone"))
        menu.addItem(action("Settings...",            sel: #selector(openSettings),
                            key: "", icon: "gearshape"))

        let role = viewModel.currentUser?.role ?? ""
        if role == "admin" || role == "superadmin" {
            menu.addItem(action("Admin Panel...", sel: #selector(openAdminPanel),
                                key: "", icon: "shield.lefthalf.filled"))
        }

        menu.addItem(action("Quit", sel: #selector(quit), key: "", icon: "power"))
        menu.addItem(.separator())
        let version = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? ""
        let build   = Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? ""
        menu.addItem(versionStatusItem(version: version, build: build, status: viewModel.statusText))

        menu.delegate = self
        statusItem?.menu = menu
    }

    // MARK: - NSMenuDelegate

    nonisolated func menuWillOpen(_ menu: NSMenu) {
        Task { @MainActor [weak self] in self?.syncUI() }
    }

    // MARK: - Actions

    @objc private func statusBarButtonClicked() {}

    @objc private func toggleRecording() {
        if viewModel.isRecording {
            viewModel.forceStop()
        } else {
            viewModel.startRecording()
        }
    }

    @objc private func forceStop() { viewModel.forceStop() }

    @objc private func restartService() { viewModel.restartBackend() }

    @objc private func switchMode(_ sender: NSMenuItem) {
        guard let raw = sender.representedObject as? String,
              let mode = AppMode(rawValue: raw) else { return }
        viewModel.selectAppMode(mode)
    }

    @objc private func openSettings() {
        if let w = settingsWindow, w.isVisible { w.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps: true); return }
        let window = NSPanel(contentRect: NSRect(x: 0, y: 0, width: 900, height: 620),
                             styleMask: [.titled, .closable, .nonactivatingPanel],
                             backing: .buffered, defer: false)
        window.contentViewController = NSHostingController(rootView: SettingsView(viewModel: viewModel))
        window.title = ""
        window.isFloatingPanel = true
        window.level = .floating
        window.titleVisibility = .hidden
        window.titlebarAppearsTransparent = true
        window.center()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        settingsWindow = window
    }

    @objc private func openITDataset() {
        itDatasetWindowController.open(viewModel: viewModel)
    }

    @objc private func openAdminPanel() {
        let baseURL = UserDefaults.standard.string(forKey: AppSettings.serverURL) ?? "http://127.0.0.1:8765"
        if let url = URL(string: "\(baseURL)/admin") {
            NSWorkspace.shared.open(url)
        }
    }

    @objc private func quit() { NSApplication.shared.terminate(nil) }

    // MARK: - Accessibility

    private func checkAccessibility() {
        if !AXIsProcessTrusted() {
            viewModel.statusText = "⚠ Enable Accessibility!"
        }
    }

    // MARK: - Helpers

    private func versionStatusItem(version: String, build: String, status: String) -> NSMenuItem {
        let item = NSMenuItem()
        item.isEnabled = false
        item.tag = 100
        item.attributedTitle = makeVersionStatusAttr(version: version, build: build, status: status)
        return item
    }

    private func makeVersionStatusAttr(version: String, build: String, status: String) -> NSAttributedString {
        let small = NSFont.menuFont(ofSize: NSFont.smallSystemFontSize)
        let tiny  = NSFont.menuFont(ofSize: NSFont.smallSystemFontSize - 1.5)
        let result = NSMutableAttributedString()
        result.append(NSAttributedString(string: status, attributes: [
            .foregroundColor: NSColor.secondaryLabelColor,
            .font: small
        ]))
        result.append(NSAttributedString(string: "  (v\(version) · \(build))", attributes: [
            .foregroundColor: NSColor.tertiaryLabelColor,
            .font: tiny
        ]))
        return result
    }

    private func disabled(_ title: String, tag: Int = 0) -> NSMenuItem {
        let item = NSMenuItem(title: title, action: nil, keyEquivalent: "")
        item.isEnabled = false
        item.tag = tag
        return item
    }

    private func action(_ title: String, sel: Selector, key: String,
                        icon: String? = nil, tag: Int = 0) -> NSMenuItem {
        let item = NSMenuItem(title: title, action: sel, keyEquivalent: key)
        item.target = self
        item.tag = tag
        if let icon, let img = NSImage(systemSymbolName: icon, accessibilityDescription: nil) {
            img.isTemplate = true   // monochrome — menü rengine uyar, multicolor bozulmaz
            item.image = img
        }
        return item
    }

}
