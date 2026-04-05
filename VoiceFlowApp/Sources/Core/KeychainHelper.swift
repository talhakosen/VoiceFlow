import Foundation
import Security

enum KeychainHelper {

    // MARK: - Core

    static func save(key: String, value: String) {
        let data = Data(value.utf8)
        let query: [String: Any] = [
            kSecClass as String:       kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecValueData as String:   data
        ]
        SecItemDelete(query as CFDictionary)
        SecItemAdd(query as CFDictionary, nil)
    }

    static func read(key: String) -> String? {
        let query: [String: Any] = [
            kSecClass as String:            kSecClassGenericPassword,
            kSecAttrAccount as String:      key,
            kSecReturnData as String:       true as CFTypeRef,
            kSecMatchLimit as String:       kSecMatchLimitOne
        ]
        var item: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &item) == errSecSuccess,
              let data = item as? Data,
              let value = String(data: data, encoding: .utf8) else { return nil }
        return value
    }

    static func delete(key: String) {
        let query: [String: Any] = [
            kSecClass as String:       kSecClassGenericPassword,
            kSecAttrAccount as String: key
        ]
        SecItemDelete(query as CFDictionary)
    }

    // MARK: - Convenience

    static var accessToken: String? {
        get { read(key: "vf_access_token") }
        set {
            if let v = newValue { save(key: "vf_access_token", value: v) }
            else { delete(key: "vf_access_token") }
        }
    }

    static var refreshToken: String? {
        get { read(key: "vf_refresh_token") }
        set {
            if let v = newValue { save(key: "vf_refresh_token", value: v) }
            else { delete(key: "vf_refresh_token") }
        }
    }
}
