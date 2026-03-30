import AppKit
import SwiftUI

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
        case .general:     return "General"
        case .engineering: return "Engineering"
        case .office:      return "Office"
        }
    }
}
