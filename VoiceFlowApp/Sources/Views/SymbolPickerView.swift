import AppKit

// MARK: - SymbolItem

struct SymbolItem {
    let name: String     // "BackendService"
    let pathKey: String  // "VoiceFlowApp/Sources/BackendService.swift"
    let line: String     // "212"
    var selected: Bool = true

    /// ref format: "BackendService → VoiceFlowApp/Sources/BackendService.swift:212"
    init(ref: String) {
        let parts = ref.components(separatedBy: " → ")
        name = parts.first?.trimmingCharacters(in: .whitespaces) ?? ref
        let fullPath = parts.count > 1 ? parts[1].trimmingCharacters(in: .whitespaces) : ""
        let pathParts = fullPath.components(separatedBy: ":")
        pathKey = pathParts.first ?? fullPath
        line = pathParts.count > 1 ? pathParts[1] : ""
    }
}

// MARK: - SymbolPickerWindowController
// NSAlert tabanlı sembol seçim diyaloğu — SwiftUI NSPanel constraint sorunlarından kaçınmak için

final class SymbolPickerWindowController: NSObject {

    func show(refs: [String], onConfirm: @escaping ([SymbolItem]) -> Void, onSkip: @escaping () -> Void) {
        var items = refs.map { SymbolItem(ref: $0) }

        let alert = NSAlert()
        alert.messageText = "Semboller tespit edildi"
        alert.informativeText = "Yapıştırmak istediklerini seç:"
        alert.alertStyle = .informational
        alert.addButton(withTitle: "Yapıştır")
        alert.addButton(withTitle: "Atla")

        // NSStackView ile checkbox listesi
        let stack = NSStackView()
        stack.orientation = .vertical
        stack.alignment = .left
        stack.spacing = 6
        stack.translatesAutoresizingMaskIntoConstraints = false

        var checkboxes: [NSButton] = []
        for item in items {
            let cb = NSButton(checkboxWithTitle: "", target: nil, action: nil)
            cb.state = .on
            let label = "\(item.name)  —  \(item.pathKey)\(item.line.isEmpty ? "" : ":\(item.line)")"
            cb.title = label
            cb.font = NSFont.monospacedSystemFont(ofSize: 11, weight: .regular)
            stack.addArrangedSubview(cb)
            checkboxes.append(cb)
        }

        let container = NSView(frame: NSRect(x: 0, y: 0, width: 460, height: CGFloat(items.count) * 26 + 8))
        container.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: container.leadingAnchor),
            stack.trailingAnchor.constraint(equalTo: container.trailingAnchor),
            stack.topAnchor.constraint(equalTo: container.topAnchor, constant: 4),
        ])
        alert.accessoryView = container

        let response = alert.runModal()

        if response == .alertSecondButtonReturn {
            // Atla
            onSkip()
            return
        }

        // Yapıştır — checkbox state'e göre seçimleri güncelle
        for (i, cb) in checkboxes.enumerated() {
            items[i].selected = cb.state == .on
        }
        onConfirm(items)
    }

    func close() {
        // NSAlert modal — programatik kapatma gerekmez
    }
}
