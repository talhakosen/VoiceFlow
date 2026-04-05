import Dependencies
import AppKit

struct DialogClient {
    var showEditDialog: (_ currentText: String) async -> DialogClient.EditResult

    enum EditResult {
        case saved(String)
        case cancelled
    }
}

extension DialogClient: DependencyKey {
    static let liveValue = DialogClient(
        showEditDialog: { currentText in
            await MainActor.run {
                let alert = NSAlert()
                alert.messageText = "Metni Duzelt"
                alert.informativeText = "Dogru metni yazin:"
                alert.alertStyle = .informational
                alert.addButton(withTitle: "Kaydet")
                alert.addButton(withTitle: "Iptal")

                let scrollView = NSScrollView(frame: NSRect(x: 0, y: 0, width: 420, height: 100))
                scrollView.hasVerticalScroller = true
                scrollView.hasHorizontalScroller = false
                scrollView.autohidesScrollers = true

                let textView = NSTextView(frame: scrollView.bounds)
                textView.string = currentText
                textView.isEditable = true
                textView.isRichText = false
                textView.font = NSFont.systemFont(ofSize: 13)
                textView.autoresizingMask = [.width]
                scrollView.documentView = textView
                alert.accessoryView = scrollView

                DispatchQueue.main.async { textView.selectAll(nil) }

                let response = alert.runModal()
                if response == .alertFirstButtonReturn {
                    let corrected = textView.string.trimmingCharacters(in: .whitespacesAndNewlines)
                    return corrected.isEmpty ? .cancelled : .saved(corrected)
                }
                return .cancelled
            }
        }
    )
    static let testValue = DialogClient(
        showEditDialog: { _ in .cancelled }
    )
}

extension DependencyValues {
    var dialogClient: DialogClient {
        get { self[DialogClient.self] }
        set { self[DialogClient.self] = newValue }
    }
}
