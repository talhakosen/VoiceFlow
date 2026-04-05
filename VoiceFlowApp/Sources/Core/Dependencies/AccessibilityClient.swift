import Dependencies
import AppKit

struct AccessibilityClient {
    var isProcessTrusted: () -> Bool
}

extension AccessibilityClient: DependencyKey {
    static let liveValue = AccessibilityClient(
        isProcessTrusted: { AXIsProcessTrusted() }
    )
    static let testValue = AccessibilityClient(
        isProcessTrusted: { true }
    )
}

extension DependencyValues {
    var accessibilityClient: AccessibilityClient {
        get { self[AccessibilityClient.self] }
        set { self[AccessibilityClient.self] = newValue }
    }
}
