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
    let itWavPath: String?
    let pendingWavPath: String?
    let symbolRefs: [String]?

    enum CodingKeys: String, CodingKey {
        case text
        case rawText = "raw_text"
        case corrected
        case snippetUsed = "snippet_used"
        case language
        case duration
        case processingMs = "processing_ms"
        case id
        case itWavPath = "it_wav_path"
        case pendingWavPath = "pending_wav_path"
        case symbolRefs = "symbol_refs"
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
    let whisperModel: String?
    let adapterVersion: String?

    enum CodingKeys: String, CodingKey {
        case status
        case modelLoaded     = "model_loaded"
        case llmLoaded       = "llm_loaded"
        case whisperModel    = "whisper_model"
        case adapterVersion  = "adapter_version"
    }
}

// MARK: - Protocol (enables mock injection for tests/previews)

protocol BackendServiceProtocol: Actor {
    func startRecording() async throws
    func stopRecording(activeAppBundleID: String?, windowTitle: String?, selectedText: String?, cmdIntervals: [(Double, Double)]?, itDatasetIndex: Int?, trainingMode: Bool) async throws -> TranscriptionResult
    func saveUserCorrection(wavPath: String, whisperText: String, correctedText: String) async throws
    func deletePendingWav(wavPath: String) async throws
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
    func loadSnippetPack(packName: String) async throws
    func clearSnippetPack(packName: String) async throws

    // Auth
    func login(email: String, password: String) async throws -> AuthTokens
    func register(email: String, password: String) async throws -> AuthUser
    func refreshToken(_ refreshToken: String) async throws -> String
    func getMe() async throws -> AuthUser

    // Training Mode (Katman 4)
    func submitFeedback(rawWhisper: String, modelOutput: String, userAction: String, userEdit: String?) async throws

    // IT Dataset (Engineering Whisper)
    func getITDatasetNext(offset: Int, trainingSet: String) async throws -> ITDatasetResponse
    func getITDatasetRandom(trainingSet: String) async throws -> ITDatasetResponse
    func getITDatasetRecorded(trainingSet: String) async throws -> [ITDatasetResponse]
    func saveITDatasetPair(index: Int, whisperOutput: String) async throws
    func deleteITDatasetPair(wavPath: String) async throws
}

// MARK: - Concrete implementation

actor BackendService: BackendServiceProtocol {
    private let session: URLSession

    static func debugLog(_ msg: String) {
        let line = "\(Date()) \(msg)\n"
        if let data = line.data(using: .utf8) {
            let path = AppConstants.swiftLogPath
            if let fh = FileHandle(forWritingAtPath: path) {
                fh.seekToEndOfFile(); fh.write(data); fh.closeFile()
            } else {
                FileManager.default.createFile(atPath: path, contents: data)
            }
        }
    }

    init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest  = AppConstants.requestTimeout
        config.timeoutIntervalForResource = AppConstants.resourceTimeout
        self.session = URLSession(configuration: config)
    }

    // MARK: - Computed config (reads UserDefaults on each call)

    private var baseURL: String {
        let mode = DeploymentMode(rawValue: UserDefaults.standard.string(forKey: AppSettings.deploymentMode) ?? "") ?? .local
        if mode == .server,
           let url = UserDefaults.standard.string(forKey: AppSettings.serverURL),
           !url.isEmpty {
            return "\(url)/api"
        }
        return AppConstants.defaultLocalAPIURL
    }

    /// Root URL without /api suffix (for auth endpoints)
    private var rootURL: String {
        let mode = DeploymentMode(rawValue: UserDefaults.standard.string(forKey: AppSettings.deploymentMode) ?? "") ?? .local
        if mode == .server,
           let url = UserDefaults.standard.string(forKey: AppSettings.serverURL),
           !url.isEmpty {
            return url
        }
        return AppConstants.defaultLocalURL
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
            request.setValue(key, forHTTPHeaderField: APIHeader.apiKey)
        }
        let uid = userID
        if !uid.isEmpty {
            request.setValue(uid, forHTTPHeaderField: APIHeader.userID)
        }
        if let token = KeychainHelper.accessToken {
            request.setValue("\(APIValue.bearer) \(token)", forHTTPHeaderField: APIHeader.authorization)
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
        let request = makeRequest(path: APIEndpoint.start, method: "POST")
        let (_, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
    }

    func stopRecording(activeAppBundleID: String? = nil, windowTitle: String? = nil, selectedText: String? = nil, cmdIntervals: [(Double, Double)]? = nil, itDatasetIndex: Int? = nil, trainingMode: Bool = false) async throws -> TranscriptionResult {
        var request = makeRequest(path: APIEndpoint.stop, method: "POST")
        if let bundleID = activeAppBundleID {
            request.setValue(bundleID, forHTTPHeaderField: APIHeader.activeApp)
        }
        if let title = windowTitle {
            request.setValue(title, forHTTPHeaderField: APIHeader.windowTitle)
        }
        if let selected = selectedText {
            request.setValue(selected, forHTTPHeaderField: APIHeader.selectedText)
        }
        if let intervals = cmdIntervals, !intervals.isEmpty {
            let header = intervals.map { "\(String(format: "%.2f", $0.0))-\(String(format: "%.2f", $0.1))" }.joined(separator: ",")
            request.setValue(header, forHTTPHeaderField: APIHeader.cmdIntervals)
        }
        if let idx = itDatasetIndex {
            request.setValue(String(idx), forHTTPHeaderField: APIHeader.itDatasetIndex)
        }
        if trainingMode {
            request.setValue("1", forHTTPHeaderField: APIHeader.trainingMode)
        }
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            NSLog("VoiceFlow stopRecording: HTTP error %d", (response as? HTTPURLResponse)?.statusCode ?? -1)
            throw BackendError.requestFailed
        }
        do {
            let result = try JSONDecoder().decode(TranscriptionResult.self, from: data)
            Self.debugLog("stopRecording OK: text='\(result.text)'")
            return result
        } catch {
            Self.debugLog("stopRecording DECODE ERROR: \(error)")
            Self.debugLog("raw JSON: \(String(data: data, encoding: .utf8) ?? "nil")")
            throw error
        }
    }

    func saveUserCorrection(wavPath: String, whisperText: String, correctedText: String) async throws {
        var request = makeRequest(path: APIEndpoint.savCorrection, method: "POST")
        let body = ["wav_path": wavPath, "whisper_text": whisperText, "corrected_text": correctedText]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        request.setValue(APIValue.contentTypeJSON, forHTTPHeaderField: APIHeader.contentType)
        let (_, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
    }

    func deletePendingWav(wavPath: String) async throws {
        var request = makeRequest(path: APIEndpoint.pendingWav, method: "DELETE")
        let body = ["wav_path": wavPath]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        request.setValue(APIValue.contentTypeJSON, forHTTPHeaderField: APIHeader.contentType)
        let (_, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
    }

    func forceStop() async throws {
        let request = makeRequest(path: APIEndpoint.forceStop, method: "POST")
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
        let request = makeRequest(path: APIEndpoint.status)
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
        var request = makeRequest(path: APIEndpoint.config, method: "POST")
        request.setValue(APIValue.contentTypeJSON, forHTTPHeaderField: APIHeader.contentType)

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
        let request = makeRequest(path: "\(APIEndpoint.history)?limit=\(limit)")
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
        return try JSONDecoder().decode(HistoryResponse.self, from: data).items
    }

    func clearHistory() async throws {
        let request = makeRequest(path: APIEndpoint.history, method: "DELETE")
        let (_, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
    }

    func getContextStatus() async throws -> ContextStatus {
        let request = makeRequest(path: APIEndpoint.contextStatus)
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
        return try JSONDecoder().decode(ContextStatus.self, from: data)
    }

    func getContextProjects() async throws -> ContextProjects {
        let request = makeRequest(path: APIEndpoint.contextProjects)
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
        return try JSONDecoder().decode(ContextProjects.self, from: data)
    }

    func ingestContext(path: String) async throws {
        var request = makeRequest(path: APIEndpoint.contextIngest, method: "POST")
        request.setValue(APIValue.contentTypeJSON, forHTTPHeaderField: APIHeader.contentType)
        request.httpBody = try JSONSerialization.data(withJSONObject: ["path": path])
        let (_, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
    }

    func clearContext() async throws {
        let request = makeRequest(path: APIEndpoint.context, method: "DELETE")
        let (_, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
    }

    func getDictionary() async throws -> [DictionaryEntry] {
        let request = makeRequest(path: APIEndpoint.dictionary)
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
        return try JSONDecoder().decode(DictionaryResponse.self, from: data).items
    }

    func addDictionaryEntry(trigger: String, replacement: String, scope: String) async throws -> DictionaryEntry {
        var request = makeRequest(path: APIEndpoint.dictionary, method: "POST")
        request.setValue(APIValue.contentTypeJSON, forHTTPHeaderField: APIHeader.contentType)
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
        let request = makeRequest(path: "\(APIEndpoint.dictionary)/\(id)", method: "DELETE")
        let (_, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
    }

    func getSnippets() async throws -> [SnippetEntry] {
        let request = makeRequest(path: APIEndpoint.snippets)
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
        return try JSONDecoder().decode(SnippetResponse.self, from: data).items
    }

    func addSnippet(triggerPhrase: String, expansion: String, scope: String) async throws -> SnippetEntry {
        var request = makeRequest(path: APIEndpoint.snippets, method: "POST")
        request.setValue(APIValue.contentTypeJSON, forHTTPHeaderField: APIHeader.contentType)
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
        let request = makeRequest(path: "\(APIEndpoint.snippets)/\(id)", method: "DELETE")
        let (_, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
    }

    func loadSnippetPack(packName: String) async throws {
        let request = makeRequest(path: "\(APIEndpoint.snippetPack)/\(packName)", method: "POST")
        let (_, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
    }

    func clearSnippetPack(packName: String) async throws {
        let request = makeRequest(path: "\(APIEndpoint.snippetPack)/\(packName)", method: "DELETE")
        let (_, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
    }

    // MARK: - Auth

    func login(email: String, password: String) async throws -> AuthTokens {
        var request = makeAuthRequest(path: APIEndpoint.authLogin)
        request.httpBody = try JSONSerialization.data(withJSONObject: ["email": email, "password": password])
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.unauthorized
        }
        return try JSONDecoder().decode(AuthTokens.self, from: data)
    }

    func register(email: String, password: String) async throws -> AuthUser {
        var request = makeAuthRequest(path: APIEndpoint.authRegister)
        request.httpBody = try JSONSerialization.data(withJSONObject: ["email": email, "password": password])
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
        return try JSONDecoder().decode(AuthUser.self, from: data)
    }

    func refreshToken(_ refreshToken: String) async throws -> String {
        var request = makeAuthRequest(path: APIEndpoint.authRefresh)
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
        var req = URLRequest(url: URL(string: "\(rootURL)/auth/\(APIEndpoint.authMe)")!)
        req.httpMethod = "GET"
        if let token = KeychainHelper.accessToken {
            req.setValue("\(APIValue.bearer) \(token)", forHTTPHeaderField: APIHeader.authorization)
        }
        let (data, _) = try await dataWithRefreshRetry(for: req)
        return try JSONDecoder().decode(AuthUser.self, from: data)
    }

    func submitFeedback(rawWhisper: String, modelOutput: String, userAction: String, userEdit: String? = nil) async throws {
        var request = makeRequest(path: APIEndpoint.feedback, method: "POST")
        request.setValue(APIValue.contentTypeJSON, forHTTPHeaderField: APIHeader.contentType)
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

struct AuthUser: Decodable, Equatable {
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

// MARK: - IT Dataset

struct ITRecordingItem: Decodable {
    let whisper: String
    let wavPath: String

    enum CodingKeys: String, CodingKey {
        case whisper
        case wavPath = "wav_path"
    }
}

struct ITDatasetResponse: Decodable {
    let index: Int
    let total: Int
    let sentence: String
    let persona: String?
    let scenario: String?
    let recordings: [ITRecordingItem]?
}

extension BackendService {
    func getITDatasetNext(offset: Int = 0, trainingSet: String = "it_dataset") async throws -> ITDatasetResponse {
        let request = makeRequest(path: "\(APIEndpoint.itDatasetNext)?offset=\(offset)&training_set=\(trainingSet)")
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
        return try JSONDecoder().decode(ITDatasetResponse.self, from: data)
    }

    func getITDatasetRandom(trainingSet: String = "it_dataset") async throws -> ITDatasetResponse {
        let request = makeRequest(path: "\(APIEndpoint.itDatasetRandom)?training_set=\(trainingSet)")
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
        return try JSONDecoder().decode(ITDatasetResponse.self, from: data)
    }

    func getITDatasetRecorded(trainingSet: String = "it_dataset") async throws -> [ITDatasetResponse] {
        let request = makeRequest(path: "\(APIEndpoint.itDatasetRecorded)?training_set=\(trainingSet)")
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
        return try JSONDecoder().decode([ITDatasetResponse].self, from: data)
    }

    func saveITDatasetPair(index: Int, whisperOutput: String) async throws {
        var request = makeRequest(path: APIEndpoint.itDatasetRecord, method: "POST")
        request.setValue(APIValue.contentTypeJSON, forHTTPHeaderField: APIHeader.contentType)
        let body: [String: Any] = ["index": index, "whisper_output": whisperOutput]
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        let (_, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
    }

    func deleteITDatasetPair(wavPath: String) async throws {
        var request = makeRequest(path: APIEndpoint.itDatasetRecord, method: "DELETE")
        request.setValue(APIValue.contentTypeJSON, forHTTPHeaderField: APIHeader.contentType)
        let body: [String: String] = ["wav_path": wavPath]
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        let (_, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
    }
}
