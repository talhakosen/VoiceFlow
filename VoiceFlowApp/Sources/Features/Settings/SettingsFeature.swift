import ComposableArchitecture
import Foundation

@Reducer
struct SettingsFeature {
    @ObservableState
    struct State {
        var dictionaryEntries: [DictionaryEntry] = []
        var snippetEntries: [SnippetEntry] = []
        var contextChunkCount: Int = 0
        var isIndexing: Bool = false
        var contextIndexingError: String? = nil
        var userName: String = ""
        var userDepartment: String = ""
        var userID: String = ""
    }

    enum Action {
        // Dictionary
        case loadDictionary
        case dictionaryLoaded([DictionaryEntry])
        case addDictionaryEntry(trigger: String, replacement: String, scope: String)
        case deleteDictionaryEntry(Int) // id
        case addWordCorrections(original: String, corrected: String)

        // Snippets
        case loadSnippets
        case snippetsLoaded([SnippetEntry])
        case addSnippet(trigger: String, expansion: String)
        case deleteSnippet(Int) // id

        // Context
        case loadContextStatus
        case contextStatusLoaded(Int)
        case ingestContext(folderPath: String)
        case contextIngested(Int)
        case contextIngestFailed(String)
        case clearContext
        case contextCleared

        // User profile
        case setUserName(String)
        case setUserDepartment(String)
    }

    @Dependency(\.backendClient) var backend

    var body: some Reducer<State, Action> {
        Reduce { state, action in
            switch action {

            // MARK: - Dictionary

            case .loadDictionary:
                return .run { send in
                    if let entries = try? await backend.getDictionary() {
                        await send(.dictionaryLoaded(entries))
                    }
                }

            case let .dictionaryLoaded(entries):
                state.dictionaryEntries = entries
                return .none

            case let .addDictionaryEntry(trigger, replacement, scope):
                return .run { send in
                    try? await backend.addDictionaryEntry(trigger, replacement, scope)
                    if let entries = try? await backend.getDictionary() {
                        await send(.dictionaryLoaded(entries))
                    }
                }

            case let .deleteDictionaryEntry(id):
                return .run { send in
                    try? await backend.deleteDictionaryEntry(id)
                    if let entries = try? await backend.getDictionary() {
                        await send(.dictionaryLoaded(entries))
                    }
                }

            case let .addWordCorrections(original, corrected):
                let origWords = original.components(separatedBy: .whitespaces).filter { !$0.isEmpty }
                let corrWords = corrected.components(separatedBy: .whitespaces).filter { !$0.isEmpty }
                guard origWords.count == corrWords.count else { return .none }
                let pairs = zip(origWords, corrWords).filter { $0.0 != $0.1 }
                return .run { send in
                    for (orig, corr) in pairs {
                        try? await backend.addDictionaryEntry(orig.lowercased(), corr, "personal")
                    }
                    if let entries = try? await backend.getDictionary() {
                        await send(.dictionaryLoaded(entries))
                    }
                }

            // MARK: - Snippets

            case .loadSnippets:
                return .run { send in
                    if let entries = try? await backend.getSnippets() {
                        await send(.snippetsLoaded(entries))
                    }
                }

            case let .snippetsLoaded(entries):
                state.snippetEntries = entries
                return .none

            case let .addSnippet(trigger, expansion):
                return .run { send in
                    try? await backend.addSnippet(trigger, expansion, "personal")
                    if let entries = try? await backend.getSnippets() {
                        await send(.snippetsLoaded(entries))
                    }
                }

            case let .deleteSnippet(id):
                return .run { send in
                    try? await backend.deleteSnippet(id)
                    if let entries = try? await backend.getSnippets() {
                        await send(.snippetsLoaded(entries))
                    }
                }

            // MARK: - Context

            case .loadContextStatus:
                return .run { send in
                    if let projects = try? await backend.getContextProjects() {
                        await send(.contextStatusLoaded(projects.smartWordCount))
                    } else if let status = try? await backend.getContextStatus() {
                        await send(.contextStatusLoaded(status.count))
                    }
                }

            case let .contextStatusLoaded(count):
                state.contextChunkCount = count
                return .none

            case let .ingestContext(folderPath):
                state.isIndexing = true
                state.contextIndexingError = nil
                return .run { send in
                    do {
                        try await backend.ingestContext(folderPath)
                        // Poll for completion (up to 30 iterations × 2s = 60s)
                        var previousCount = -1
                        for _ in 0..<30 {
                            try? await Task.sleep(nanoseconds: 2_000_000_000)
                            if let projects = try? await backend.getContextProjects() {
                                let total = projects.totalSymbols
                                if total > 0 && total == previousCount {
                                    await send(.contextIngested(projects.smartWordCount))
                                    return
                                }
                                previousCount = total
                            }
                        }
                        // Fallback: return whatever count we have
                        if let projects = try? await backend.getContextProjects() {
                            await send(.contextIngested(projects.smartWordCount))
                        } else {
                            await send(.contextIngested(0))
                        }
                    } catch {
                        await send(.contextIngestFailed(error.localizedDescription))
                    }
                }

            case let .contextIngested(count):
                state.isIndexing = false
                state.contextChunkCount = count
                return .none

            case let .contextIngestFailed(error):
                state.isIndexing = false
                state.contextIndexingError = error
                return .none

            case .clearContext:
                return .run { send in
                    try? await backend.clearContext()
                    await send(.contextCleared)
                }

            case .contextCleared:
                state.contextChunkCount = 0
                return .none

            // MARK: - User profile

            case let .setUserName(name):
                state.userName = name
                UserDefaults.standard.set(name, forKey: AppSettings.userName)
                return .none

            case let .setUserDepartment(dept):
                state.userDepartment = dept
                UserDefaults.standard.set(dept, forKey: AppSettings.userDepartment)
                return .none
            }
        }
    }
}
