import ComposableArchitecture
import Foundation

@Reducer
struct HistoryFeature {
    @ObservableState
    struct State {
        var entries: [HistoryItem] = []
        var isLoading: Bool = false
        var searchQuery: String = ""
        var error: String? = nil

        var filteredEntries: [HistoryItem] {
            guard !searchQuery.isEmpty else { return entries }
            return entries.filter {
                $0.text.localizedCaseInsensitiveContains(searchQuery)
            }
        }
    }

    enum Action {
        case appeared
        case entriesLoaded([HistoryItem])
        case loadFailed(String)
        case deleteAllTapped
        case allDeleted
        case searchQueryChanged(String)
        case copyEntryTapped(String)
    }

    @Dependency(\.backendClient) var backend

    var body: some Reducer<State, Action> {
        Reduce { state, action in
            switch action {
            case .appeared:
                state.isLoading = true
                return .run { send in
                    do {
                        let entries = try await backend.getHistory(AppConstants.historyFetchLimit)
                        await send(.entriesLoaded(entries))
                    } catch {
                        await send(.loadFailed(error.localizedDescription))
                    }
                }

            case let .entriesLoaded(entries):
                state.isLoading = false
                state.entries = entries
                return .none

            case let .loadFailed(msg):
                state.isLoading = false
                state.error = msg
                return .none

            case .deleteAllTapped:
                return .run { send in
                    try? await backend.clearHistory()
                    await send(.allDeleted)
                }

            case .allDeleted:
                state.entries = []
                return .none

            case let .searchQueryChanged(query):
                state.searchQuery = query
                return .none

            case .copyEntryTapped:
                return .none // handled by NSPasteboard at view level
            }
        }
    }
}
