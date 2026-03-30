import Foundation

struct TranscriptionResult: Codable {
    let text: String
    let rawText: String?
    let corrected: Bool?
    let language: String?
    let duration: Double?
    let id: Int?

    enum CodingKeys: String, CodingKey {
        case text
        case rawText = "raw_text"
        case corrected
        case language
        case duration
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

struct StatusResponse: Codable {
    let status: String
    let isRecording: Bool

    enum CodingKeys: String, CodingKey {
        case status
        case isRecording = "is_recording"
    }
}

actor BackendService {
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
        return request
    }

    // MARK: - API

    func startRecording() async throws {
        let request = makeRequest(path: "start", method: "POST")
        let (_, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BackendError.requestFailed
        }
    }

    func stopRecording() async throws -> TranscriptionResult {
        let request = makeRequest(path: "stop", method: "POST")
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
}

enum BackendError: Error {
    case requestFailed
    case decodingFailed
    case backendNotRunning
}
