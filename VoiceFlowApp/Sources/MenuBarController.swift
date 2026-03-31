import AppKit
import SwiftUI

// MARK: - MenuBarController
// Responsibility: NSStatusItem + NSMenu setup and updates.
// All business logic is in AppViewModel.

@MainActor
class MenuBarController: NSObject {
    private var statusItem: NSStatusItem?
    private let viewModel: AppViewModel
    private var settingsWindow: NSWindow?
    private var mySpaceWindow: NSWindow?
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
            self?.syncUI()
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

        // Status text
        menu.item(withTag: 100)?.title = viewModel.statusText

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

        menu.addItem(disabled("Ready", tag: 100))
        menu.addItem(.separator())
        menu.addItem(action("Toggle Recording", sel: #selector(toggleRecording), key: "r"))
        menu.addItem(action("Force Stop",       sel: #selector(forceStop),       key: "s"))
        menu.addItem(.separator())
        menu.addItem(action("Kisisel Alan",     sel: #selector(openMySpace),     key: "m"))
        menu.addItem(action("Settings...",      sel: #selector(openSettings),    key: ","))
        let role = viewModel.currentUser?.role ?? ""
        if role == "admin" || role == "superadmin" {
            menu.addItem(action("Admin Panel...", sel: #selector(openAdminPanel), key: ""))
        }
        menu.addItem(action("Quit",             sel: #selector(quit),            key: "q"))

        statusItem?.menu = menu
    }

    // MARK: - Actions

    @objc private func statusBarButtonClicked() {}

    @objc private func toggleRecording() {
        if viewModel.isRecording {
            Task { await viewModel.stopAndTranscribe() }
        } else {
            viewModel.startRecording()
        }
    }

    @objc private func forceStop() { viewModel.forceStop() }

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

    func openMySpaceFromViewModel() {
        openMySpace()
    }

    @objc private func openMySpace() {
        if let w = mySpaceWindow, w.isVisible { w.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps: true); return }
        let view = MySpaceView(viewModel: viewModel)
        let window = NSPanel(contentRect: NSRect(x: 0, y: 0, width: 680, height: 560),
                             styleMask: [.titled, .closable, .nonactivatingPanel],
                             backing: .buffered, defer: false)
        window.contentViewController = NSHostingController(rootView: view)
        window.title = "Kişisel Alan"
        window.isFloatingPanel = true
        window.level = .floating
        window.delegate = self
        window.center()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        mySpaceWindow = window
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

}

// MARK: - NSWindowDelegate

extension MenuBarController: NSWindowDelegate {
    func windowWillClose(_ notification: Notification) {
        if (notification.object as? NSWindow) === mySpaceWindow {
            mySpaceWindow = nil
        }
    }
}
