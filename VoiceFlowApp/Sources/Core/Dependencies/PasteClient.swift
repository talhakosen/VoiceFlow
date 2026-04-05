import Dependencies
import Foundation

struct PasteClient {
    var paste: (String) -> Void
    var copyToClipboard: (String) -> Void
}

extension PasteClient: DependencyKey {
    static let liveValue = PasteClient(
        paste: { text in
            PasteService().pasteText(text)
        },
        copyToClipboard: { text in
            PasteService().copyToClipboard(text)
        }
    )
    static let testValue = PasteClient(
        paste: { _ in },
        copyToClipboard: { _ in }
    )
}

extension DependencyValues {
    var pasteClient: PasteClient {
        get { self[PasteClient.self] }
        set { self[PasteClient.self] = newValue }
    }
}
