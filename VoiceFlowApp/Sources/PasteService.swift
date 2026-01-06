import AppKit
import Carbon

class PasteService {
    func pasteText(_ text: String) {
        print("PasteService: Pasting text: \(text)")

        // Copy to clipboard
        let pasteboard = NSPasteboard.general
        pasteboard.clearContents()
        pasteboard.setString(text, forType: .string)

        // Simulate Cmd+V using AppleScript after delay
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
            self.simulatePasteWithAppleScript()
        }
    }

    private func simulatePasteWithAppleScript() {
        let script = """
        tell application "System Events"
            keystroke "v" using command down
        end tell
        """

        if let appleScript = NSAppleScript(source: script) {
            var error: NSDictionary?
            appleScript.executeAndReturnError(&error)
            if let error = error {
                print("PasteService: AppleScript error: \(error)")
            } else {
                print("PasteService: Paste command sent via AppleScript")
            }
        }
    }

    func copyToClipboard(_ text: String) {
        let pasteboard = NSPasteboard.general
        pasteboard.clearContents()
        pasteboard.setString(text, forType: .string)
    }
}
