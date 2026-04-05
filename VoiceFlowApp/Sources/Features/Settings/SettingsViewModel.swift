import Foundation
import Observation

/// Settings-only state — dictionary, snippets, knowledge base, user profile.
/// Completely isolated from the recording pipeline.
@Observable
@MainActor
final class SettingsViewModel {

    // MARK: - Dictionary
    var dictionaryEntries: [DictionaryEntry] = []

    // MARK: - Snippets
    var snippetEntries: [SnippetEntry] = []

    // MARK: - Knowledge Base
    var contextChunkCount: Int = 0
    var indexedProjects: [IndexedProject] = []
    var isIndexing: Bool = false
    var contextIndexingError: String? = nil

    // MARK: - User Profile
    var userName: String = UserDefaults.standard.string(forKey: AppSettings.userName) ?? "" {
        didSet { UserDefaults.standard.set(userName, forKey: AppSettings.userName) }
    }
    var userDepartment: String = UserDefaults.standard.string(forKey: AppSettings.userDepartment) ?? "" {
        didSet { UserDefaults.standard.set(userDepartment, forKey: AppSettings.userDepartment) }
    }
    var userID: String = UserDefaults.standard.string(forKey: AppSettings.userID) ?? ""

    // MARK: - Dependencies
    private let backend: any BackendServiceProtocol

    init(backend: any BackendServiceProtocol) {
        self.backend = backend
    }

    // MARK: - Dictionary

    func loadDictionary() {
        Task { dictionaryEntries = (try? await backend.getDictionary()) ?? [] }
    }

    func addDictionaryEntry(trigger: String, replacement: String, scope: String) {
        Task {
            if let entry = try? await backend.addDictionaryEntry(trigger: trigger, replacement: replacement, scope: scope) {
                dictionaryEntries.append(entry)
            }
        }
    }

    func deleteDictionaryEntry(id: Int) {
        Task {
            try? await backend.deleteDictionaryEntry(id: id)
            dictionaryEntries.removeAll { $0.id == id }
        }
    }

    // MARK: - Snippets

    func loadSnippets() {
        Task { snippetEntries = (try? await backend.getSnippets()) ?? [] }
    }

    func addSnippet(triggerPhrase: String, expansion: String, scope: String) {
        Task {
            if let entry = try? await backend.addSnippet(triggerPhrase: triggerPhrase, expansion: expansion, scope: scope) {
                snippetEntries.append(entry)
            }
        }
    }

    func deleteSnippet(id: Int) {
        Task {
            try? await backend.deleteSnippet(id: id)
            snippetEntries.removeAll { $0.id == id }
        }
    }

    // MARK: - Knowledge Base

    func loadContextStatus() {
        Task {
            if let projects = try? await backend.getContextProjects() {
                indexedProjects = projects.projects
                contextChunkCount = projects.smartWordCount
            } else if let status = try? await backend.getContextStatus() {
                contextChunkCount = status.count
            }
        }
    }

    func ingestContext(folderPath: String) {
        isIndexing = true
        contextIndexingError = nil
        Task {
            do {
                try await backend.ingestContext(path: folderPath)
                var previousCount = -1
                for _ in 0..<30 {
                    try? await Task.sleep(nanoseconds: 2_000_000_000)
                    if let projects = try? await backend.getContextProjects() {
                        indexedProjects = projects.projects
                        contextChunkCount = projects.smartWordCount
                        let total = projects.totalSymbols
                        if total > 0 && total == previousCount { break }
                        previousCount = total
                    }
                }
            } catch {
                contextIndexingError = error.localizedDescription
            }
            isIndexing = false
        }
    }

    func clearContext() {
        Task {
            try? await backend.clearContext()
            contextChunkCount = 0
            indexedProjects = []
        }
    }
}
