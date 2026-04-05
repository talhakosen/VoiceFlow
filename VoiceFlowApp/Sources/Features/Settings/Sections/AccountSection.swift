import SwiftUI
import AppKit

// MARK: - Account

struct AccountSection: View {
    var settingsVM: SettingsViewModel
    var viewModel: AppViewModel

    @State private var userName: String
    @State private var userDepartment: String

    init(settingsVM: SettingsViewModel, viewModel: AppViewModel) {
        self.settingsVM = settingsVM
        self.viewModel = viewModel
        _userName       = State(initialValue: settingsVM.userName)
        _userDepartment = State(initialValue: settingsVM.userDepartment)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: VFSpacing.xxl) {

            VFSectionHeader("Profil")
            VFCard {
                VFRow("Ad Soyad") {
                    TextField("Opsiyonel", text: $userName)
                        .textFieldStyle(.roundedBorder)
                        .frame(minWidth: VFLayout.fieldMedium)
                        .onChange(of: userName) { settingsVM.userName = userName }
                }
                VFRow("Departman") {
                    TextField("Opsiyonel", text: $userDepartment)
                        .textFieldStyle(.roundedBorder)
                        .frame(minWidth: VFLayout.fieldMedium)
                        .onChange(of: userDepartment) { settingsVM.userDepartment = userDepartment }
                }
                VFRow("Kullanıcı ID",
                      divider: viewModel.currentUser == nil) {
                    Text(settingsVM.userID.isEmpty ? "—" : settingsVM.userID)
                        .font(.system(.caption, design: .monospaced))
                        .foregroundStyle(.secondary)
                }
                if let user = viewModel.currentUser {
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
