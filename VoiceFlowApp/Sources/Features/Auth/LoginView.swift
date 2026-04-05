import SwiftUI

struct LoginView: View {
    var viewModel: AppViewModel

    @State private var email = ""
    @State private var password = ""
    @State private var isLoading = false

    var body: some View {
        VStack(spacing: VFSpacing.xxxl) {
            // Logo / icon
            Image(systemName: VFIcon.appLogoFill)
                .font(VFFont.largeIcon)
                .foregroundStyle(VFColor.primary)
                .padding(.top, VFSpacing.huge)

            Text("VoiceFlow")
                .font(VFFont.title)

            Divider()

            VStack(spacing: VFSpacing.xl) {
                TextField("E-posta", text: $email)
                    .textFieldStyle(.roundedBorder)
                    .textContentType(.emailAddress)
                    .disableAutocorrection(true)

                SecureField("Şifre", text: $password)
                    .textFieldStyle(.roundedBorder)
                    .textContentType(.password)
                    .onSubmit { submitLogin() }
            }
            .padding(.horizontal, VFSpacing.max)

            if let error = viewModel.loginError {
                Text(error)
                    .font(VFFont.caption)
                    .foregroundStyle(VFColor.destructive)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, VFSpacing.max)
            }

            Button(action: submitLogin) {
                ZStack {
                    if isLoading {
                        ProgressView()
                            .scaleEffect(0.8)
                    } else {
                        Text("Giriş Yap")
                            .fontWeight(.semibold)
                    }
                }
                .frame(maxWidth: .infinity)
                .frame(height: 32)
            }
            .buttonStyle(.borderedProminent)
            .padding(.horizontal, VFSpacing.max)
            .disabled(isLoading || email.isEmpty || password.isEmpty)

            Text("Hesabın yok mu? Yöneticinizle iletişime geçin.")
                .font(VFFont.caption)
                .foregroundStyle(.secondary)
                .padding(.bottom, VFSpacing.huge)
        }
        .frame(width: VFLayout.WindowSize.login.width, height: VFLayout.WindowSize.login.height)
    }

    private func submitLogin() {
        guard !isLoading, !email.isEmpty, !password.isEmpty else { return }
        isLoading = true
        Task {
            await viewModel.login(email: email, password: password)
            isLoading = false
        }
    }
}
