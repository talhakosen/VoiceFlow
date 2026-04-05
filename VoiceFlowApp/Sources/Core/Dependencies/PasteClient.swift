import Dependencies
import Foundation

struct PasteClient {
    var paste: @Sendable (String) async -> Void
    var copyToClipboard: @Sendable (String) async -> Void
}

extension PasteClient: DependencyKey {
    static let liveValue = PasteClient(
        paste: { text in
            await MainActor.run { PasteService().pasteText(text) }
        },
        copyToClipboard: { text in
            await MainActor.run { PasteService().copyToClipboard(text) }
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
