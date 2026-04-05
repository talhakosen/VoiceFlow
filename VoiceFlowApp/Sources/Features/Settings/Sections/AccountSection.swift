import ComposableArchitecture
import SwiftUI
import AppKit

// MARK: - Account

struct AccountSection: View {
    let settingsStore: StoreOf<SettingsFeature>
    // Fix 1: currentUser lives in AuthFeature, not RecordingFeature
    let authStore: StoreOf<AuthFeature>

    @State private var userName: String
    @State private var userDepartment: String

    init(settingsStore: StoreOf<SettingsFeature>, authStore: StoreOf<AuthFeature>) {
        self.settingsStore = settingsStore
        self.authStore = authStore
        _userName       = State(initialValue: settingsStore.state.userName)
        _userDepartment = State(initialValue: settingsStore.state.userDepartment)
    }

    var body: some View {
        let settingsState = settingsStore.state
        let authState = authStore.state
        VStack(alignment: .leading, spacing: VFSpacing.xxl) {

            VFSectionHeader("Profil")
            VFCard {
                VFRow("Ad Soyad") {
                    TextField("Opsiyonel", text: $userName)
                        .textFieldStyle(.roundedBorder)
                        .frame(minWidth: VFLayout.fieldMedium)
                        .onChange(of: userName) { settingsStore.send(.setUserName(userName)) }
                }
                VFRow("Departman") {
                    TextField("Opsiyonel", text: $userDepartment)
                        .textFieldStyle(.roundedBorder)
                        .frame(minWidth: VFLayout.fieldMedium)
                        .onChange(of: userDepartment) { settingsStore.send(.setUserDepartment(userDepartment)) }
                }
                VFRow("Kullanıcı ID",
                      divider: authState.currentUser == nil) {
                    Text(settingsState.userID.isEmpty ? "—" : settingsState.userID)
                        .font(.system(.caption, design: .monospaced))
                        .foregroundStyle(.secondary)
                }
                if let user = authState.currentUser {
                    VFRow("Rol", divider: false) {
                        Text(user.role.capitalized)
                            .foregroundStyle(user.role == "admin" || user.role == "superadmin"
                                             ? VFColor.primary : .secondary)
                    }
                }
            }
        }
        .padding(VFSpacing.xxxl)
    }
}
