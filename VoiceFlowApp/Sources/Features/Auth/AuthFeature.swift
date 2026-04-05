import ComposableArchitecture
import Foundation

// MARK: - AuthFeature

/// TCA Reducer for authentication.
/// `backend.login` returns `AuthTokens`; we persist tokens to Keychain,
/// then call `backend.getMe` to resolve the `AuthUser`.
@Reducer
struct AuthFeature {

    @ObservableState
    struct State: Equatable {
        var isLoggedIn: Bool = false
        var currentUser: AuthUser? = nil
        var isLoading: Bool = false
        var loginError: String? = nil
        var serverURL: String = AppConstants.defaultLocalURL
        var email: String = ""
        var password: String = ""
    }

    enum Action: Equatable {
        case loginTapped
        case loginResponse(Result<AuthUser, AuthFeatureError>)
        case logoutTapped
        case tokenRefreshAttempted
        case serverURLChanged(String)
        case emailChanged(String)
        case passwordChanged(String)
    }

    // Equatable-conforming error wrapper so Action stays Equatable.
    enum AuthFeatureError: Error, Equatable {
        case message(String)
    }

    @Dependency(\.backendClient) var backend

    var body: some Reducer<State, Action> {
        Reduce { state, action in
            switch action {

            case .loginTapped:
                guard !state.email.isEmpty, !state.password.isEmpty else { return .none }
                state.isLoading = true
                state.loginError = nil
                let email = state.email
                let password = state.password
                return .run { send in
                    do {
                        let tokens = try await backend.login(email, password)
                        // Persist tokens to Keychain.
                        await MainActor.run {
                            KeychainHelper.accessToken  = tokens.accessToken
                            KeychainHelper.refreshToken = tokens.refreshToken
                        }
                        let user = try await backend.getMe()
                        await send(.loginResponse(.success(user)))
                    } catch {
                        await send(.loginResponse(.failure(.message(error.localizedDescription))))
                    }
                }

            case let .loginResponse(.success(user)):
                state.isLoading = false
                state.isLoggedIn = true
                state.currentUser = user
                state.password = ""
                return .none

            case let .loginResponse(.failure(error)):
                state.isLoading = false
                if case let .message(msg) = error {
                    state.loginError = msg
                }
                return .none

            case .logoutTapped:
                state.isLoggedIn = false
                state.currentUser = nil
                state.email = ""
                state.password = ""
                KeychainHelper.accessToken  = nil
                KeychainHelper.refreshToken = nil
                return .none

            case .tokenRefreshAttempted:
                guard let storedRefresh = KeychainHelper.refreshToken else { return .none }
                return .run { _ in
                    _ = try? await backend.refreshToken(storedRefresh)
                }

            case let .serverURLChanged(url):
                state.serverURL = url
                return .none

            case let .emailChanged(email):
                state.email = email
                return .none

            case let .passwordChanged(password):
                state.password = password
                return .none
            }
        }
    }
}
