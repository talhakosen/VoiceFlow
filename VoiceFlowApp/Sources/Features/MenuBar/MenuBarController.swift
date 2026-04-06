import AppKit
import ComposableArchitecture
import SwiftUI

// MARK: - MenuBarController
// Responsibility: NSStatusItem + NSMenu setup and updates.
// All business logic is in the TCA Store.

@MainActor
class MenuBarController: NSObject, NSMenuDelegate {
    private var statusItem: NSStatusItem?
    private let store: StoreOf<AppFeature>
    private var settingsWindow: NSWindow?
    private var settingsDialogWindow: NSWindow?
    private var itDatasetWindowController = ITDatasetWindowController()
    private var lastKnownRole: String = ""
    private var updateTimer: Timer?

    init(store: StoreOf<AppFeature>) {
        self.store = store
        super.init()
        setupStatusItem()
        checkAccessibility()
        observeStore()
    }

    // MARK: - Status Item

    private func setupStatusItem() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        guard let button = statusItem?.button else { return }
        if let img = NSImage(named: "MenuBarIcon") {
            img.isTemplate = true
            button.image = img
        } else {
            button.image = NSImage(systemSymbolName: "waveform", accessibilityDescription: "VoiceFlow")
        }
        button.action = #selector(statusBarButtonClicked)
        button.target = self
        rebuildMenu()
    }

    // MARK: - Store observation

    private func observeStore() {
        updateTimer = Timer.scheduledTimer(withTimeInterval: 0.3, repeats: true) { [weak self] _ in
            Task { @MainActor [weak self] in self?.syncUI() }
        }
    }

    deinit {
        updateTimer?.invalidate()
    }

    private var recordingState: RecordingFeature.State { store.recording }

    private func syncUI() {
        guard let menu = statusItem?.menu else { return }

        // Rebuild if role changed — read from AuthFeature (source of truth)
        let currentRole = store.auth.currentUser?.role ?? ""
        if currentRole != lastKnownRole {
            lastKnownRole = currentRole
            rebuildMenu()
            return
        }

        // Recording toggle (tag 101)
        let recording = recordingState.isRecording
        if let recItem = menu.item(withTag: 101) {
            recItem.title = recording ? "Kaydı Durdur" : "Kaydı Başlat"
        }

        // Paste last transcript (tag 102) — enabled only when a result exists
        if let pasteItem = menu.item(withTag: 102) {
            pasteItem.isEnabled = recordingState.lastResult != nil
        }

        // Mode checkmarks in submenu
        for item in menu.items {
            if item.tag == 103, let sub = item.submenu {
                for subItem in sub.items {
                    if let raw = subItem.representedObject as? String,
                       let mode = AppMode(rawValue: raw) {
                        subItem.state = recordingState.currentAppMode == mode ? .on : .off
                    }
                }
            }
            if item.tag == 104, let sub = item.submenu {
                for subItem in sub.items {
                    if let raw = subItem.representedObject as? String,
                       let lang = LanguageMode(rawValue: raw) {
                        subItem.state = recordingState.currentLanguageMode == lang ? .on : .off
                    }
                }
            }
        }

        // Status bar icon
        let button = statusItem?.button
        if recording {
            button?.image = NSImage(systemSymbolName: "waveform.circle.fill", accessibilityDescription: "VoiceFlow")
            button?.contentTintColor = .systemRed
        } else {
            if let img = NSImage(named: "MenuBarIcon") {
                img.isTemplate = true
                button?.image = img
            } else {
                button?.image = NSImage(systemSymbolName: "waveform", accessibilityDescription: "VoiceFlow")
            }
            button?.contentTintColor = nil
        }
    }

    // MARK: - Menu construction

    private func rebuildMenu() {
        let menu = NSMenu()

        // ── Branding header ──────────────────────────────────────────────
        menu.addItem(brandHeader())
        menu.addItem(.separator())

        // ── Home ─────────────────────────────────────────────────────────
        menu.addItem(action("Ana Ekran", sel: #selector(openSettings), key: ","))
        menu.addItem(.separator())

        // ── Primary action ───────────────────────────────────────────────
        let isRec = recordingState.isRecording
        menu.addItem(action(isRec ? "Kaydı Durdur" : "Kaydı Başlat",
                            sel: #selector(toggleRecording),
                            key: "", tag: 101))

        let pasteItem = action("Son Transkripsiyonu Yapıştır",
                               sel: #selector(pasteLastTranscript),
                               key: "v", tag: 102)
        pasteItem.keyEquivalentModifierMask = [.control, .command]
        pasteItem.isEnabled = recordingState.lastResult != nil
        menu.addItem(pasteItem)
        menu.addItem(.separator())

        // ── Config submenus ──────────────────────────────────────────────

        let langMenu = NSMenu()
        for lang in LanguageMode.allCases {
            let item = action(lang.rawValue, sel: #selector(switchLanguage(_:)), key: "")
            item.representedObject = lang.rawValue
            item.state = recordingState.currentLanguageMode == lang ? .on : .off
            langMenu.addItem(item)
        }
        let langItem = NSMenuItem(title: "Dil", action: nil, keyEquivalent: "")
        langItem.tag = 104
        langItem.submenu = langMenu
        menu.addItem(langItem)

        let modeMenu = NSMenu()
        for (idx, mode) in AppMode.allCases.enumerated() {
            let item = action(mode.displayName, sel: #selector(switchMode(_:)), key: "\(idx + 1)")
            item.keyEquivalentModifierMask = .option
            item.representedObject = mode.rawValue
            item.state = recordingState.currentAppMode == mode ? .on : .off
            modeMenu.addItem(item)
        }
        let modeItem = NSMenuItem(title: "Kullanım Alanı", action: nil, keyEquivalent: "")
        modeItem.tag = 103
        modeItem.submenu = modeMenu
        menu.addItem(modeItem)

        menu.addItem(.separator())

        // ── Tools ────────────────────────────────────────────────────────
        menu.addItem(action("Ses Eğitimi…", sel: #selector(openITDataset), key: ""))

        let role = store.auth.currentUser?.role ?? ""
        if role == "admin" || role == "superadmin" {
            menu.addItem(action("Admin Panel…", sel: #selector(openAdminPanel), key: ""))
        }

        menu.addItem(.separator())

        // ── Service ──────────────────────────────────────────────────────
        menu.addItem(action("Servisi Yeniden Başlat", sel: #selector(restartService), key: ""))
        menu.addItem(.separator())

        // ── Quit ─────────────────────────────────────────────────────────
        menu.addItem(action("VoiceFlow'dan Çık", sel: #selector(quit), key: "q", icon: "power"))

        menu.delegate = self
        statusItem?.menu = menu
    }

    private func brandHeader() -> NSMenuItem {
        let item = NSMenuItem()
        item.isEnabled = false
        let version = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? ""
        let attr = NSMutableAttributedString()
        attr.append(NSAttributedString(string: "VoiceFlow", attributes: [
            .font: NSFont.menuFont(ofSize: NSFont.systemFontSize),
            .foregroundColor: NSColor.labelColor
        ]))
        attr.append(NSAttributedString(string: "  v\(version)", attributes: [
            .font: NSFont.menuFont(ofSize: NSFont.smallSystemFontSize),
            .foregroundColor: NSColor.tertiaryLabelColor
        ]))
        item.attributedTitle = attr
        return item
    }

    // MARK: - NSMenuDelegate

    nonisolated func menuWillOpen(_ menu: NSMenu) {
        Task { @MainActor [weak self] in self?.syncUI() }
    }

    // MARK: - Actions

    @objc private func statusBarButtonClicked() {}

    @objc private func toggleRecording() {
        if recordingState.isRecording {
            store.send(.recording(.forceStop))
        } else {
            store.send(.recording(.startRecording))
        }
    }

    @objc private func pasteLastTranscript() {
        store.send(.recording(.pasteLastResult))
    }

    @objc private func restartService() {
        store.send(.recording(.restartBackend))
    }

    @objc private func switchLanguage(_ sender: NSMenuItem) {
        guard let raw = sender.representedObject as? String,
              let lang = LanguageMode(rawValue: raw) else { return }
        store.send(.recording(.selectLanguageMode(lang)))
    }

    @objc private func switchMode(_ sender: NSMenuItem) {
        guard let raw = sender.representedObject as? String,
              let mode = AppMode(rawValue: raw) else { return }
        store.send(.recording(.selectAppMode(mode)))
    }

    @objc private func openSettings() {
        if let w = settingsWindow, w.isVisible { w.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps: true); return }

        // Ekran boyutunun %85'i — Wispr Flow gibi geniş açılır
        let screen = NSScreen.screens.first(where: {
            NSMouseInRect(NSEvent.mouseLocation, $0.frame, false)
        }) ?? NSScreen.main ?? NSScreen.screens[0]
        let sf = screen.visibleFrame
        let winW = (sf.width  * 0.92).rounded()
        let winH = (sf.height * 0.92).rounded()
        let ox   = (sf.minX + (sf.width  - winW) / 2).rounded()
        let oy   = (sf.minY + (sf.height - winH) / 2).rounded()

        let window = NSPanel(contentRect: NSRect(x: ox, y: oy, width: winW, height: winH),
                             styleMask: [.titled, .closable, .miniaturizable, .resizable, .fullSizeContentView],
                             backing: .buffered, defer: false)
        window.title = ""
        window.isFloatingPanel = false
        window.level = .normal
        window.titleVisibility = .hidden
        window.titlebarAppearsTransparent = true
        window.toolbarStyle = .unified
        window.backgroundColor = NSColor.windowBackgroundColor
        window.minSize = NSSize(width: 960, height: 640)

        let rootView = MainContentView(store: store, onOpenSettings: { [weak self] in
            self?.openSettingsDialog()
        })
        let hosting = NSHostingController(rootView: rootView)
        hosting.view.frame = NSRect(x: 0, y: 0, width: winW, height: winH)
        window.contentView = hosting.view

        // setFrame zorla — SwiftUI intrinsic size'ın ezilmesini önler
        window.setFrame(NSRect(x: ox, y: oy, width: winW, height: winH), display: false)
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        settingsWindow = window
    }

    @objc func openSettingsDialog() {
        if let w = settingsDialogWindow, w.isVisible { w.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps: true); return }
        let size = VFLayout.WindowSize.settingsDialog
        let window = NSPanel(
            contentRect: NSRect(x: 0, y: 0, width: size.width, height: size.height),
            styleMask: [.titled, .closable, .fullSizeContentView],
            backing: .buffered,
            defer: false
        )
        window.title = "Ayarlar"
        window.isFloatingPanel = false
        window.level = .normal
        window.titleVisibility = .hidden
        window.titlebarAppearsTransparent = true
        window.backgroundColor = NSColor.windowBackgroundColor
        window.isMovableByWindowBackground = true
        let hosting = NSHostingController(rootView: SettingsDialogView(store: store))
        window.contentView = hosting.view
        window.makeKeyAndOrderFront(nil)
        DispatchQueue.main.async {
            let targetScreen = NSScreen.screens.first(where: {
                NSMouseInRect(NSEvent.mouseLocation, $0.frame, false)
            }) ?? NSScreen.main ?? NSScreen.screens[0]
            let sf = targetScreen.visibleFrame
            let ox = sf.minX + (sf.width - size.width) / 2
            let oy = sf.minY + (sf.height - size.height) / 2
            window.setFrameOrigin(NSPoint(x: ox, y: oy))
        }
        NSApp.activate(ignoringOtherApps: true)
        settingsDialogWindow = window
    }

    @objc private func openITDataset() {
        itDatasetWindowController.open(store: store)
    }

    @objc private func openAdminPanel() {
        let baseURL = UserDefaults.standard.string(forKey: AppSettings.serverURL) ?? AppConstants.defaultLocalURL
        if let url = URL(string: "\(baseURL)/admin") {
            NSWorkspace.shared.open(url)
        }
    }

    @objc private func quit() { NSApplication.shared.terminate(nil) }

    // MARK: - Accessibility

    private func checkAccessibility() {
        if !AXIsProcessTrusted() {
            store.send(.recording(.recordingFailed("Enable Accessibility!")))
        }
    }

    // MARK: - Helpers

    private func action(_ title: String, sel: Selector, key: String,
                        icon: String? = nil, tag: Int = 0) -> NSMenuItem {
        let item = NSMenuItem(title: title, action: sel, keyEquivalent: key)
        item.target = self
        item.tag = tag
        if let icon, let img = NSImage(systemSymbolName: icon, accessibilityDescription: nil) {
            img.isTemplate = true
            item.image = img
        }
        return item
    }

}
