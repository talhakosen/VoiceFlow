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
    private let baseURL = "http://127.0.0.1:8765/api"
    private let session: URLSession

    init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 60
        self.session = URLSession(configuration: config)
    }

    func startRecording() async throws {
        let url = URL(string: "\(baseURL)/start")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"

        let (_, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw BackendError.requestFailed
        }
    }

    func stopRecording() async throws -> TranscriptionResult {
        let url = URL(string: "\(baseURL)/stop")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw BackendError.requestFailed
        }

        let decoder = JSONDecoder()
        return try decoder.decode(TranscriptionResult.self, from: data)
    }

    func getStatus() async throws -> StatusResponse {
        let url = URL(string: "\(baseURL)/status")!
        let (data, response) = try await session.data(from: url)

        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw BackendError.requestFailed
        }

        let decoder = JSONDecoder()
        return try decoder.decode(StatusResponse.self, from: data)
    }

    func isBackendRunning() async -> Bool {
        do {
            _ = try await getStatus()
            return true
        } catch {
            return false
        }
    }

    func updateConfig(language: String?, task: String, correctionEnabled: Bool? = nil) async throws {
        let url = URL(string: "\(baseURL)/config")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        var body: [String: Any] = ["task": task]
        if let language = language {
            body["language"] = language
        } else {
            body["language"] = NSNull()
        }
        if let correctionEnabled = correctionEnabled {
            body["correction_enabled"] = correctionEnabled
        }

        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (_, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw BackendError.requestFailed
        }
    }
}

enum BackendError: Error {
    case requestFailed
    case decodingFailed
    case backendNotRunning
}
