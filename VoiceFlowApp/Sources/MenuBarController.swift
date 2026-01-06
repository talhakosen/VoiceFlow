import AppKit
import SwiftUI

class MenuBarController: NSObject {
    private var statusItem: NSStatusItem?
    private var popover: NSPopover?
    private let backendService = BackendService()
    private let hotkeyManager = HotkeyManager()
    private let pasteService = PasteService()

    private var isRecording = false

    override init() {
        super.init()
        setupStatusItem()
        setupHotkey()
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

        menu.addItem(NSMenuItem.separator())

        let quitItem = NSMenuItem(title: "Quit", action: #selector(quit), keyEquivalent: "q")
        quitItem.target = self
        menu.addItem(quitItem)

        self.statusItem?.menu = menu
    }

    @objc private func togglePopover() {
        // For now, just show menu
    }

    @objc private func quit() {
        NSApplication.shared.terminate(nil)
    }

    // MARK: - Hotkey

    private func setupHotkey() {
        hotkeyManager.onDoubleTapFn = { [weak self] in
            self?.handleDoubleTapFn()
        }

        hotkeyManager.onFnKeyDown = { [weak self] in
            self?.startRecording()
        }

        hotkeyManager.onFnKeyUp = { [weak self] in
            self?.stopRecordingAndTranscribe()
        }

        hotkeyManager.start()
    }

    private func handleDoubleTapFn() {
        print("Double-tap Fn detected - Push-to-talk mode activated")
    }

    // MARK: - Recording

    private func startRecording() {
        guard !isRecording else { return }
        isRecording = true

        updateStatusIcon(recording: true)

        Task {
            do {
                try await backendService.startRecording()
                print("Recording started")
            } catch {
                print("Failed to start recording: \(error)")
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

        Task {
            do {
                let result = try await backendService.stopRecording()
                print("Transcription: \(result.text)")

                if !result.text.isEmpty {
                    await MainActor.run {
                        pasteService.pasteText(result.text)
                    }
                }
            } catch {
                print("Failed to stop/transcribe: \(error)")
            }
        }
    }

    private func updateStatusIcon(recording: Bool) {
        DispatchQueue.main.async { [weak self] in
            if let button = self?.statusItem?.button {
                let symbolName = recording ? "waveform.circle.fill" : "waveform"
                button.image = NSImage(systemSymbolName: symbolName, accessibilityDescription: "VoiceFlow")

                // Tint red when recording
                if recording {
                    button.contentTintColor = .systemRed
                } else {
                    button.contentTintColor = nil
                }
            }

            // Update menu status
            if let menu = self?.statusItem?.menu,
               let statusItem = menu.item(withTag: 100) {
                statusItem.title = recording ? "Recording..." : "Ready"
            }
        }
    }
}
