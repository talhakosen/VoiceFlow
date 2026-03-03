import AppKit
import Carbon

class PasteService {
    var hasAccessibility: Bool {
        AXIsProcessTrusted()
    }

    func pasteText(_ text: String) {
        NSLog("VoiceFlow PasteService: Pasting text: '%@'", text)

        // Check accessibility permission
        if !hasAccessibility {
            NSLog("VoiceFlow PasteService: WARNING - No accessibility permission! CGEvent paste will fail.")
            NSLog("VoiceFlow PasteService: Go to System Settings > Privacy & Security > Accessibility > Enable VoiceFlow")
        }

        // Copy to clipboard
        let pasteboard = NSPasteboard.general
        pasteboard.clearContents()
        let success = pasteboard.setString(text, forType: .string)
        NSLog("VoiceFlow PasteService: Clipboard set: %@", success ? "YES" : "NO")

        // Simulate Cmd+V using CGEvent
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) { [weak self] in
            self?.simulatePasteWithCGEvent()
        }
    }

    private func simulatePasteWithCGEvent() {
        let src = CGEventSource(stateID: .hidSystemState)

        guard let keyDown = CGEvent(keyboardEventSource: src, virtualKey: 0x09, keyDown: true),
              let keyUp = CGEvent(keyboardEventSource: src, virtualKey: 0x09, keyDown: false) else {
            NSLog("VoiceFlow PasteService: ERROR - Failed to create CGEvent")
            return
        }

        keyDown.flags = .maskCommand
        keyDown.post(tap: .cghidEventTap)

        keyUp.flags = .maskCommand
        keyUp.post(tap: .cghidEventTap)

        NSLog("VoiceFlow PasteService: Cmd+V sent via CGEvent (accessibility: %@)", hasAccessibility ? "YES" : "NO")
    }

    func copyToClipboard(_ text: String) {
        let pasteboard = NSPasteboard.general
        pasteboard.clearContents()
        pasteboard.setString(text, forType: .string)
    }
}
