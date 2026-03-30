import SwiftUI

@main
struct WhisperFlowApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate

    var body: some Scene {
        // Settings window is managed as NSPanel by MenuBarController (NSPanel pattern).
        // SwiftUI Settings scene is unreliable in debug builds.
        Settings { EmptyView() }
    }
}
