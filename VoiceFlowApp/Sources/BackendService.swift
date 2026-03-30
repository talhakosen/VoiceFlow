import Foundation

struct TranscriptionResult: Codable {
    let text: String
    let rawText: String?
    let corrected: Bool?
    let language: String?
    let duration: Double?

    enum CodingKeys: String, CodingKey {
        case text
        case rawText = "raw_text"
        case corrected
        case language
        case duration
    }
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

    private func makeRequest(path: String, method: String = "GET") -> URLRequest {
        let url = URL(string: "\(baseURL)/\(path)")!
        var request = URLRequest(url: url)
        request.httpMethod = method
        let key = apiKey
        if !key.isEmpty {
            request.setValue(key, forHTTPHeaderField: "X-API-Key")
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

    func updateConfig(language: String?, task: String, correctionEnabled: Bool? = nil) async throws {
        var request = makeRequest(path: "config", method: "POST")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        var body: [String: Any] = ["task": task]
        body["language"] = language ?? NSNull()
        if let correctionEnabled {
            body["correction_enabled"] = correctionEnabled
        }
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
}
