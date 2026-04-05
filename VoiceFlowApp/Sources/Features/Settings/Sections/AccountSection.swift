import ComposableArchitecture
import SwiftUI
import AppKit

// MARK: - Account

struct AccountSection: View {
    let settingsStore: StoreOf<SettingsFeature>
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
        VStack(alignment: .leading, spacing: 28) {

            Text("Hesap")
                .font(.system(size: 22, weight: .bold))
                .padding(.bottom, 4)

            // Profil
            SettingsCardSection(title: "Profil") {
                SettingsRow(title: "Ad Soyad", subtitle: "Transkripsiyon geçmişinde görünür", isLast: false) {
                    TextField("Opsiyonel", text: $userName)
                        .textFieldStyle(.roundedBorder)
                        .frame(minWidth: VFLayout.fieldMedium)
                        .onChange(of: userName) { settingsStore.send(.setUserName(userName)) }
                }
                SettingsRow(title: "Departman", subtitle: "Raporlama ve istatistiklerde kullanılır", isLast: true) {
                    TextField("Opsiyonel", text: $userDepartment)
                        .textFieldStyle(.roundedBorder)
                        .frame(minWidth: VFLayout.fieldMedium)
                        .onChange(of: userDepartment) { settingsStore.send(.setUserDepartment(userDepartment)) }
                }
            }

            // Kimlik
            SettingsCardSection(title: "Kimlik") {
                SettingsRow(
                    title: "Kullanıcı ID",
                    subtitle: "Bu cihaza özgü benzersiz tanımlayıcı",
                    isLast: authState.currentUser == nil
                ) {
                    Text(settingsState.userID.isEmpty ? "—" : settingsState.userID)
                        .font(.system(.caption, design: .monospaced))
                        .foregroundStyle(.secondary)
                }
                if let user = authState.currentUser {
                    SettingsRow(title: "E-posta", subtitle: "Sunucu hesabınız", isLast: false) {
                        Text(user.email).foregroundStyle(.secondary).font(.system(size: 13))
                    }
                    SettingsRow(title: "Rol", subtitle: "Sistem yöneticisi tarafından atanır", isLast: true) {
                        Text(user.role.capitalized)
                            .foregroundStyle(
                                user.role == "admin" || user.role == "superadmin"
                                    ? VFColor.primary : .secondary
                            )
                            .font(.system(size: 13, weight: .medium))
                    }
                }
            }

            Spacer()
        }
        .padding(VFSpacing.xxxl)
    }
}
