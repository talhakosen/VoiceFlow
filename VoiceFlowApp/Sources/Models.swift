import AppKit
import SwiftUI

// MARK: - UserDefaults Keys

enum AppSettings {
    static let deploymentMode      = "deploymentMode"
    static let serverURL           = "serverURL"
    static let apiKey              = "apiKey"
    static let appMode             = "appMode"
    static let onboardingComplete  = "onboardingComplete"
    static let defaultLanguage     = "defaultLanguage"
    static let userID              = "userID"
    static let userName            = "userName"
    static let userDepartment      = "userDepartment"
    static let llmMode             = "llmMode"      // "local" | "cloud" | "alibaba"
    static let llmEndpoint         = "llmEndpoint"  // cloud Ollama URL
    static let trainingMode        = "trainingMode"    // Bool — show feedback pill after paste
    static let correctionEnabled   = "correctionEnabled" // Bool — persisted per-mode preference
    static let appearanceMode      = "appearanceMode"  // "system" | "light" | "dark"
}

// MARK: - AppearanceMode

enum AppearanceMode: String, CaseIterable {
    case system = "system"
    case light  = "light"
    case dark   = "dark"

    var displayName: String {
        switch self {
        case .system: return "Sistem"
        case .light:  return "Açık"
        case .dark:   return "Koyu"
        }
    }

    var nsAppearance: NSAppearance? {
        switch self {
        case .system: return nil
        case .light:  return NSAppearance(named: .aqua)
        case .dark:   return NSAppearance(named: .darkAqua)
        }
    }
}

// MARK: - LanguageMode

enum LanguageMode: String, CaseIterable {
    case auto                = "Auto Detect"
    case turkish             = "Türkçe"
    case english             = "English"
    case translateToEnglish  = "Any → English"

    var language: String? {
        switch self {
        case .auto, .translateToEnglish: return nil
        case .turkish:  return "tr"
        case .english:  return "en"
        }
    }

    var task: String {
        self == .translateToEnglish ? "translate" : "transcribe"
    }
}

// MARK: - AppMode

enum AppMode: String, CaseIterable {
    case general     = "general"
    case engineering = "engineering"
    case office      = "office"

    var displayName: String {
        switch self {
        case .general:     return "Genel"
        case .engineering: return "Mühendislik"
        case .office:      return "Ofis"
        }
    }

    var menuKeyEquivalent: String {
        switch self {
        case .general:     return "1"
        case .engineering: return "2"
        case .office:      return "3"
        }
    }

    var menuIcon: String {
        switch self {
        case .general:     return "text.bubble"
        case .engineering: return "chevron.left.forwardslash.chevron.right"
        case .office:      return "envelope"
        }
    }
}
