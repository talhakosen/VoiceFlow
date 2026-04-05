import Dependencies
import AppKit

struct SoundClient {
    var play: (String) -> Void
}

extension SoundClient: DependencyKey {
    static let liveValue = SoundClient(
        play: { name in NSSound(named: name)?.play() }
    )
    static let testValue = SoundClient(play: { _ in })
}

extension DependencyValues {
    var soundClient: SoundClient {
        get { self[SoundClient.self] }
        set { self[SoundClient.self] = newValue }
    }
}
