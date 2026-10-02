import Dependencies
import Foundation

struct BackendClient {
    // MARK: - Recording
    var startRecording: () async throws -> Void
    var stopRecording: (
        _ activeAppBundleID: String?,
        _ windowTitle: String?,
        _ selectedText: String?,
        _ trainingMode: Bool
    ) async throws -> TranscriptionResult
    var forceStop: () async throws -> Void

    // MARK: - Status
    var getHealth: () async throws -> HealthResponse
    var getStatus: () async throws -> StatusResponse
    var isBackendRunning: () async -> Bool

    // MARK: - Config
    var updateConfig: (
        _ language: String?,
        _ task: String,
        _ correctionEnabled: Bool?,
        _ mode: String?
    ) async throws -> Void

    // MARK: - Audio input
    var getInputDevices: () async throws -> [AudioInputDevice]
    var setInputDevice: (_ name: String) async throws -> Void

    // MARK: - History
    var getHistory: (_ limit: Int) async throws -> [HistoryItem]
    var clearHistory: () async throws -> Void

    // MARK: - Context
    var getContextStatus: () async throws -> ContextStatus
    var ingestContext: (_ path: String) async throws -> Void
    var clearContext: () async throws -> Void

    // MARK: - Dictionary
    var getDictionary: () async throws -> [DictionaryEntry]
    var addDictionaryEntry: (
        _ trigger: String,
        _ replacement: String,
        _ scope: String
    ) async throws -> DictionaryEntry
    var deleteDictionaryEntry: (_ id: Int) async throws -> Void
    var learnDictionary: () async throws -> Int

    // MARK: - Auth
    var login: (_ email: String, _ password: String) async throws -> AuthTokens
    var register: (_ email: String, _ password: String) async throws -> AuthUser
    var refreshToken: (_ refreshToken: String) async throws -> String
    var getMe: () async throws -> AuthUser

    // MARK: - Training feedback
    var submitFeedback: (
        _ rawWhisper: String,
        _ modelOutput: String,
        _ userAction: String,
        _ userEdit: String?
    ) async throws -> Void
    var saveUserCorrection: (
        _ wavPath: String,
        _ whisperText: String,
        _ correctedText: String
    ) async throws -> Void
    var deletePendingWav: (_ wavPath: String) async throws -> Void
}

extension BackendClient: DependencyKey {
    static let liveValue: BackendClient = {
        let service = BackendService()
        return BackendClient(
            startRecording: {
                try await service.startRecording()
            },
            stopRecording: { bundleID, windowTitle, selectedText, trainingMode in
                try await service.stopRecording(
                    activeAppBundleID: bundleID,
                    windowTitle: windowTitle,
                    selectedText: selectedText,
                    trainingMode: trainingMode
                )
            },
            forceStop: {
                try await service.forceStop()
            },
            getHealth: {
                try await service.getHealth()
            },
            getStatus: {
                try await service.getStatus()
            },
            isBackendRunning: {
                await service.isBackendRunning()
            },
            updateConfig: { language, task, correctionEnabled, mode in
                try await service.updateConfig(
                    language: language,
                    task: task,
                    correctionEnabled: correctionEnabled,
                    mode: mode
                )
            },
            getInputDevices: {
                try await service.getInputDevices()
            },
            setInputDevice: { name in
                try await service.setInputDevice(name)
            },
            getHistory: { limit in
                try await service.getHistory(limit: limit)
            },
            clearHistory: {
                try await service.clearHistory()
            },
            getContextStatus: {
                try await service.getContextStatus()
            },
            ingestContext: { path in
                try await service.ingestContext(path: path)
            },
            clearContext: {
                try await service.clearContext()
            },
            getDictionary: {
                try await service.getDictionary()
            },
            addDictionaryEntry: { trigger, replacement, scope in
                try await service.addDictionaryEntry(trigger: trigger, replacement: replacement, scope: scope)
            },
            deleteDictionaryEntry: { id in
                try await service.deleteDictionaryEntry(id: id)
            },
            learnDictionary: {
                try await service.learnDictionary()
            },
            login: { email, password in
                try await service.login(email: email, password: password)
            },
            register: { email, password in
                try await service.register(email: email, password: password)
            },
            refreshToken: { token in
                try await service.refreshToken(token)
            },
            getMe: {
                try await service.getMe()
            },
            submitFeedback: { rawWhisper, modelOutput, userAction, userEdit in
                try await service.submitFeedback(
                    rawWhisper: rawWhisper,
                    modelOutput: modelOutput,
                    userAction: userAction,
                    userEdit: userEdit
                )
            },
            saveUserCorrection: { wavPath, whisperText, correctedText in
                try await service.saveUserCorrection(
                    wavPath: wavPath,
                    whisperText: whisperText,
                    correctedText: correctedText
                )
            },
            deletePendingWav: { wavPath in
                try await service.deletePendingWav(wavPath: wavPath)
            }
        )
    }()

    static let testValue = BackendClient(
        startRecording: {},
        stopRecording: { _, _, _, _ in
            TranscriptionResult(
                text: "",
                rawText: nil,
                corrected: nil,
                language: nil,
                duration: nil,
                processingMs: nil,
                id: nil,
                pendingWavPath: nil,
                notice: nil
            )
        },
        forceStop: {},
        getHealth: {
            HealthResponse(
                status: "healthy",
                modelLoaded: true,
                llmLoaded: false,
                whisperModel: nil,
                adapterVersion: nil
            )
        },
        getStatus: {
            StatusResponse(status: "idle", isRecording: false)
        },
        isBackendRunning: { true },
        updateConfig: { _, _, _, _ in },
        getInputDevices: { [] },
        setInputDevice: { _ in },
        getHistory: { _ in [] },
        clearHistory: {},
        getContextStatus: {
            ContextStatus(count: 0, isReady: true, isEmpty: true)
        },
        ingestContext: { _ in },
        clearContext: {},
        getDictionary: { [] },
        addDictionaryEntry: { trigger, replacement, scope in
            DictionaryEntry(id: 0, trigger: trigger, replacement: replacement, scope: scope, userId: nil, tenantId: nil)
        },
        deleteDictionaryEntry: { _ in },
        learnDictionary: { 0 },
        login: { _, _ in
            AuthTokens(accessToken: "", refreshToken: "", tokenType: "bearer")
        },
        register: { _, _ in
            AuthUser(userId: "", email: "", tenantId: "", role: "user")
        },
        refreshToken: { _ in "" },
        getMe: {
            AuthUser(userId: "", email: "", tenantId: "", role: "user")
        },
        submitFeedback: { _, _, _, _ in },
        saveUserCorrection: { _, _, _ in },
        deletePendingWav: { _ in }
    )
}

extension DependencyValues {
    var backendClient: BackendClient {
        get { self[BackendClient.self] }
        set { self[BackendClient.self] = newValue }
    }
}
