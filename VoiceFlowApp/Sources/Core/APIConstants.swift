import Foundation

// MARK: - APIEndpoint
// Backend API path'leri — string literal yerine her zaman bunları kullan.

enum APIEndpoint {
    static let start           = "start"
    static let stop            = "stop"
    static let forceStop       = "force-stop"
    static let status          = "status"
    static let config          = "config"
    static let history         = "history"
    static let devices         = "devices"
    static let contextIngest   = "context/ingest"
    static let contextStatus   = "context/status"
    static let context         = "context"
    static let dictionary      = "dictionary"
    static let snippets        = "snippets"
    static let snippetPack     = "snippets/pack"
    static let itDataset         = "it-dataset"
    static let itDatasetNext     = "it-dataset/next"
    static let itDatasetRandom   = "it-dataset/random"
    static let itDatasetRecorded = "it-dataset/recorded"
    static let itDatasetRecord   = "it-dataset/record"
    static let savCorrection     = "training/save-correction"
    static let pendingWav        = "training/pending-wav"
    static let feedback          = "feedback"
    static let contextProjects   = "context/projects"

    // Auth (rootURL/auth/*)
    static let authLogin    = "login"
    static let authRegister = "register"
    static let authRefresh  = "refresh"
    static let authMe       = "me"
}

// MARK: - APIHeader
// HTTP header isimleri — string literal yerine her zaman bunları kullan.

enum APIHeader {
    static let apiKey         = "X-API-Key"
    static let userID         = "X-User-ID"
    static let authorization  = "Authorization"
    static let contentType    = "Content-Type"
    static let activeApp      = "X-Active-App"
    static let windowTitle    = "X-Window-Title"
    static let selectedText   = "X-Selected-Text"
    static let cmdIntervals   = "X-Cmd-Intervals"
    static let itDatasetIndex = "X-IT-Dataset-Index"
    static let trainingMode   = "X-Training-Mode"
}

// MARK: - APIValue
// Sabit header değerleri.

enum APIValue {
    static let contentTypeJSON = "application/json"
    static let bearer          = "Bearer"
}
