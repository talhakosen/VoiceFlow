import Dependencies
import Foundation

struct UserDefaultsClient {
    var bool: (String) -> Bool
    var setBool: (Bool, String) -> Void
    var string: (String) -> String?
    var setString: (String?, String) -> Void
    var integer: (String) -> Int
    var setInteger: (Int, String) -> Void
}

extension UserDefaultsClient: DependencyKey {
    static let liveValue = UserDefaultsClient(
        bool: { UserDefaults.standard.bool(forKey: $0) },
        setBool: { UserDefaults.standard.set($0, forKey: $1) },
        string: { UserDefaults.standard.string(forKey: $0) },
        setString: { UserDefaults.standard.set($0, forKey: $1) },
        integer: { UserDefaults.standard.integer(forKey: $0) },
        setInteger: { UserDefaults.standard.set($0, forKey: $1) }
    )
    static let testValue = UserDefaultsClient(
        bool: { _ in false },
        setBool: { _, _ in },
        string: { _ in nil },
        setString: { _, _ in },
        integer: { _ in 0 },
        setInteger: { _, _ in }
    )
}

extension DependencyValues {
    var userDefaultsClient: UserDefaultsClient {
        get { self[UserDefaultsClient.self] }
        set { self[UserDefaultsClient.self] = newValue }
    }
}
