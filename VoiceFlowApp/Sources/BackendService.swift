import Foundation

struct TranscriptionResult: Codable {
    let text: String
    let rawText: String?
    let corrected: Bool?
    let snippetUsed: Bool?
    let language: String?
    let duration: Double?
    let processingMs: Int?
    let id: Int?

    enum CodingKeys: String, CodingKey {
        case text
        case rawText = "raw_text"
        case corrected
        case snippetUsed = "snippet_used"
        case language
        case duration
        case processingMs = "processing_ms"
        case id
    }
}

struct HistoryItem: Identifiable {
    let id: Int
    let createdAt: String
    let text: String
    let rawText: String?
    let corrected: Bool
    let language: String?
    let duration: Double?
    let mode: String?
}

extension HistoryItem: Decodable {
    enum CodingKeys: String, CodingKey {
        case id, text, language, duration, mode
        case createdAt = "created_at"
        case rawText   = "raw_text"
        case corrected
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id        = try c.decode(Int.self,     forKey: .id)
        createdAt = try c.decode(String.self,  forKey: .createdAt)
        text      = try c.decode(String.self,  forKey: .text)
        rawText   = try c.decodeIfPresent(String.self, forKey: .rawText)
        language  = try c.decodeIfPresent(String.self, forKey: .language)
        duration  = try c.decodeIfPresent(Double.self, forKey: .duration)
        mode      = try c.decodeIfPresent(String.self, forKey: .mode)
        // SQLite stores 0/1; decode as Int then convert to Bool
        corrected = (try c.decode(Int.self, forKey: .corrected)) != 0
    }
}

struct HistoryResponse: Decodable {
    let items: [HistoryItem]
    let count: Int
}

struct ContextStatus: Decodable {
    let count: Int
    let isReady: Bool
    let isEmpty: Bool

    enum CodingKeys: String, CodingKey {
        case count
        case isReady  = "is_ready"
        case isEmpty  = "is_empty"
    }
}

struct IndexedProject: Decodable, Identifiable {
    var id: String { path }
    let path: String
    let name: String
    let symbolCount: Int

    enum CodingKeys: String, CodingKey {
        case path, name
        case symbolCount = "symbol_count"
    }
}

struct ContextProjects: Decodable {
    let projects: [IndexedProject]
    let smartWordCount: Int
    let totalSymbols: Int

    enum CodingKeys: String, CodingKey {
        case projects
        case smartWordCount = "smart_word_count"
        case totalSymbols   = "total_symbols"
    }
}

struct DictionaryEntry: Codable, Identifiable {
    let id: Int
    let trigger: String
    let replacement: String
    let scope: String
    let userId: String?
    let tenantId: String?

    enum CodingKeys: String, CodingKey {
        case id, trigger, replacement, scope
        case userId   = "user_id"
        case tenantId = "tenant_id"
    }
}

struct DictionaryResponse: Decodable {
    let items: [DictionaryEntry]
    let count: Int
}

struct SnippetEntry: Codable, Identifiable {
    let id: Int
    let triggerPhrase: String
    let expansion: String
    let scope: String
    let userId: String?
    let tenantId: String?

    enum CodingKeys: String, CodingKey {
        case id, expansion, scope
        case triggerPhrase = "trigger_phrase"
        case userId        = "user_id"
        case tenantId      = "tenant_id"
    }
}

struct SnippetResponse: Decodable {
    let items: [SnippetEntry]
    let count: Int
}

struct StatusResponse: Codable {
    let status: String
    let isRecording: Bool

    enum CodingKeys: String, CodingKey {
        case status
        case isRecording = "is_recording"
    }
}

struct HealthResponse: Decodable {
    let status: String
    let modelLoaded: Bool
    let llmLoaded: Bool

    enum CodingKeys: String, CodingKey {
        case status
        case modelLoaded = "model_loaded"
        case llmLoaded   = "llm_loaded"
    }
}

// MARK: - Protocol (enables mock injection for tests/previews)

protocol BackendServiceProtocol: Actor {
    func startRecording() async throws
    func stopRecording(activeAppBundleID: String?, windowTitle: String?, selectedText: String?) async throws -> TranscriptionResult
    func forceStop() async throws
    func getHealth() async throws -> HealthResponse
    func getStatus() async throws -> StatusResponse
    func isBackendRunning() async -> Bool
    func updateConfig(language: String?, task: String, correctionEnabled: Bool?, mode: String?) async throws
    func getHistory(limit: Int) async throws -> [HistoryItem]
    func clearHistory() async throws
    func getContextStatus() async throws -> ContextStatus
    func getContextProjects() async throws -> ContextProjects
    func ingestContext(path: String) async throws
    func clearContext() async throws
    func getDictionary() async throws -> [DictionaryEntry]
    func addDictionaryEntry(trigger: String, replacement: String, scope: String) async throws -> DictionaryEntry
    func deleteDictionaryEntry(id: Int) async throws
    func getSnippets() async throws -> [SnippetEntry]
    func addSnippet(triggerPhrase: String, expansion: String, scope: String) async throws -> SnippetEntry
    func deleteSnippet(id: Int) async throws

    // Auth
    func login(email: String, password: String) async throws -> AuthTokens
    func register(email: String, password: String) async throws -> AuthUser
    func refreshToken(_ refreshToken: String) async throws -> String
    func getMe() async throws -> AuthUser

    // Training Mode (Katman 4)
    func submitFeedback(rawWhisper: String, modelOutput: String, userAction: String, userEdit: String?) async throws
}

// MARK: - Concrete implementation

actor BackendService: BackendServiceProtocol {
    private let session: URLSession

    init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 60
        self.session = URLSession(configuration: config)
    }

    // MARK: - Computed config (reads UserDefaults on each call)

    private var baseURL: String {
        let mode = UserDefaults.standard.string(forKey: AppSettings.deploymentMode) ?? "local"
        if mode == "server",
           let url = UserDefaults.standard.string(forKey: AppSettings.serverURL),
           !url.isEmpty {
            return "\(url)/api"
        }
        return "http://127.0.0.1:8765/api"
    }

    /// Root URL without /api suffix (for auth endpoints)
    private var rootURL: String {
        let mode = UserDefaults.standard.string(forKey: AppSettings.deploymentMode) ?? "local"
        if mode == "server",
           let url = UserDefaults.standard.string(forKey: AppSettings.serverURL),
           !url.isEmpty {
            return url
        }
        return "http://127.0.0.1:8765"
    }

    private var apiKey: String {
        UserDefaults.standard.string(forKey: AppSettings.apiKey) ?? ""
    }

    // MARK: - Request factory

    private var userID: String {
        UserDefaults.standard.string(forKey: AppSettings.userID) ?? ""
    }

    private func makeRequest(path: String, method: String = "GET") -> URLRequest {
        let url = URL(string: "\(baseURL)/\(path)")!
        var request = URLRequest(url: url)
        request.httpMethod = method
        let key = apiKey
        if !key.isEmpty {
            request.setValue(key, forHTTPHeaderField: "X-API-Key")
        }
        let uid = userID
        if !uid.isEmpty {
            request.setValue(uid, forHTTPHeaderField: "X-User-ID")
        }
        if let token = KeychainHelper.accessToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        return request
    }

    /// Build a request to /auth/* endpoints (no /api prefix, no auth header injection).
    private func makeAuthRequest(path: String, method: String = "POST") -> URLRequest {
        let url = URL(string: "\(rootURL)/auth/\(path)")!
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        return request
    }

    /// Execute a request and retry once with refreshed token on 401.
    private func dataWithRefreshRetry(for request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        var req = request
        let (data, response) = try await session.data(for: req)
        guard let http = response as? HTTPURLResponse else { throw BackendError.requestFailed }
        if http.statusCode != 401 { return (data, http) }

        // Try to refresh
        guard let rt = KeychainHelper.refreshToken else { throw BackendError.unauthorized }
        let newToken = try await refreshToken(rt)

        // Rebuild request with new token
        req.setValue("Bearer \(newToken)", forHTTPHeaderField: "Authorization")
        let (data2, response2) = try await session.data(for: req)
        guard let http2 = response2 as? HTTPURLResponse else { throw BackendError.requestFailed }
        if http2.statusCode == 401 { throw BackendError.unauthorized }
        return (data2, http2)
    }

    // MARK: - API

    func startRecording() async throws {
        let request = makeRequest(path: "start", method: "POST")
        let (_, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
    }

    func stopRecording(activeAppBundleID: String? = nil, windowTitle: String? = nil, selectedText: String? = nil) async throws -> TranscriptionResult {
        var request = makeRequest(path: "stop", method: "POST")
        if let bundleID = activeAppBundleID {
            request.setValue(bundleID, forHTTPHeaderField: "X-Active-App")
        }
        if let title = windowTitle {
            request.setValue(title, forHTTPHeaderField: "X-Window-Title")
        }
        if let selected = selectedText {
            request.setValue(selected, forHTTPHeaderField: "X-Selected-Text")
        }
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
        return try JSONDecoder().decode(TranscriptionResult.self, from: data)
    }

    func forceStop() async throws {
        let request = makeRequest(path: "force-stop", method: "POST")
        let (_, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
    }

    func getHealth() async throws -> HealthResponse {
        let healthURL = baseURL.replacingOccurrences(of: "/api", with: "") + "/health"
        var request = URLRequest(url: URL(string: healthURL)!)
        request.timeoutInterval = 3
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
        return try JSONDecoder().decode(HealthResponse.self, from: data)
    }

    func getStatus() async throws -> StatusResponse {
        let request = makeRequest(path: "status")
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
        return try JSONDecoder().decode(StatusResponse.self, from: data)
    }

    func isBackendRunning() async -> Bool {
        do { _ = try await getStatus(); return true }
        catch { return false }
    }

    func updateConfig(language: String?, task: String, correctionEnabled: Bool? = nil, mode: String? = nil) async throws {
        var request = makeRequest(path: "config", method: "POST")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        var body: [String: Any] = ["task": task]
        body["language"] = language ?? NSNull()
        if let correctionEnabled {
            body["correction_enabled"] = correctionEnabled
        }
        if let mode {
            body["mode"] = mode
        }
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (_, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
    }

    func getHistory(limit: Int = 100) async throws -> [HistoryItem] {
        let request = makeRequest(path: "history?limit=\(limit)")
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
        return try JSONDecoder().decode(HistoryResponse.self, from: data).items
    }

    func clearHistory() async throws {
        let request = makeRequest(path: "history", method: "DELETE")
        let (_, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
    }

    func getContextStatus() async throws -> ContextStatus {
        let request = makeRequest(path: "context/status")
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
        return try JSONDecoder().decode(ContextStatus.self, from: data)
    }

    func getContextProjects() async throws -> ContextProjects {
        let request = makeRequest(path: "context/projects")
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
        return try JSONDecoder().decode(ContextProjects.self, from: data)
    }

    func ingestContext(path: String) async throws {
        var request = makeRequest(path: "context/ingest", method: "POST")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: ["path": path])
        let (_, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
    }

    func clearContext() async throws {
        let request = makeRequest(path: "context", method: "DELETE")
        let (_, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
    }

    func getDictionary() async throws -> [DictionaryEntry] {
        let request = makeRequest(path: "dictionary")
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
        return try JSONDecoder().decode(DictionaryResponse.self, from: data).items
    }

    func addDictionaryEntry(trigger: String, replacement: String, scope: String) async throws -> DictionaryEntry {
        var request = makeRequest(path: "dictionary", method: "POST")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: [
            "trigger": trigger, "replacement": replacement, "scope": scope
        ])
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
        return try JSONDecoder().decode(DictionaryEntry.self, from: data)
    }

    func deleteDictionaryEntry(id: Int) async throws {
        let request = makeRequest(path: "dictionary/\(id)", method: "DELETE")
        let (_, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
    }

    func getSnippets() async throws -> [SnippetEntry] {
        let request = makeRequest(path: "snippets")
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
        return try JSONDecoder().decode(SnippetResponse.self, from: data).items
    }

    func addSnippet(triggerPhrase: String, expansion: String, scope: String) async throws -> SnippetEntry {
        var request = makeRequest(path: "snippets", method: "POST")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: [
            "trigger_phrase": triggerPhrase, "expansion": expansion, "scope": scope
        ])
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
        return try JSONDecoder().decode(SnippetEntry.self, from: data)
    }

    func deleteSnippet(id: Int) async throws {
        let request = makeRequest(path: "snippets/\(id)", method: "DELETE")
        let (_, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
    }

    // MARK: - Auth

    func login(email: String, password: String) async throws -> AuthTokens {
        var request = makeAuthRequest(path: "login")
        request.httpBody = try JSONSerialization.data(withJSONObject: ["email": email, "password": password])
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.unauthorized
        }
        return try JSONDecoder().decode(AuthTokens.self, from: data)
    }

    func register(email: String, password: String) async throws -> AuthUser {
        var request = makeAuthRequest(path: "register")
        request.httpBody = try JSONSerialization.data(withJSONObject: ["email": email, "password": password])
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
        return try JSONDecoder().decode(AuthUser.self, from: data)
    }

    func refreshToken(_ refreshToken: String) async throws -> String {
        var request = makeAuthRequest(path: "refresh")
        request.httpBody = try JSONSerialization.data(withJSONObject: ["refresh_token": refreshToken])
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.unauthorized
        }
        let tokens = try JSONDecoder().decode(RefreshTokens.self, from: data)
        KeychainHelper.accessToken = tokens.accessToken
        return tokens.accessToken
    }

    func getMe() async throws -> AuthUser {
        var req = URLRequest(url: URL(string: "\(rootURL)/auth/me")!)
        req.httpMethod = "GET"
        if let token = KeychainHelper.accessToken {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        let (data, _) = try await dataWithRefreshRetry(for: req)
        return try JSONDecoder().decode(AuthUser.self, from: data)
    }

    func submitFeedback(rawWhisper: String, modelOutput: String, userAction: String, userEdit: String? = nil) async throws {
        var request = makeRequest(path: "feedback", method: "POST")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        var body: [String: Any] = [
            "raw_whisper": rawWhisper,
            "model_output": modelOutput,
            "user_action": userAction,
        ]
        if let edit = userEdit { body["user_edit"] = edit }
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        let (_, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
    }
}

enum BackendError: Error {
    case requestFailed
    case decodingFailed
    case backendNotRunning
    case unauthorized
}

// MARK: - Auth models

struct AuthTokens: Decodable {
    let accessToken: String
    let refreshToken: String
    let tokenType: String
    enum CodingKeys: String, CodingKey {
        case accessToken  = "access_token"
        case refreshToken = "refresh_token"
        case tokenType    = "token_type"
    }
}

struct AuthUser: Decodable {
    let userId: String
    let email: String
    let tenantId: String
    let role: String
    enum CodingKeys: String, CodingKey {
        case userId   = "user_id"
        case email
        case tenantId = "tenant_id"
        case role
    }
}

struct RefreshTokens: Decodable {
    let accessToken: String
    let tokenType: String
    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case tokenType   = "token_type"
    }
}
