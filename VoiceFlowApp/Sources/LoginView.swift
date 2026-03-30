import SwiftUI

struct LoginView: View {
    var viewModel: AppViewModel

    @State private var email = ""
    @State private var password = ""
    @State private var isLoading = false

    var body: some View {
        VStack(spacing: 20) {
            // Logo / icon
            Image(systemName: "waveform.circle.fill")
                .font(.system(size: 56))
                .foregroundStyle(.blue)
                .padding(.top, 24)

            Text("VoiceFlow")
                .font(.title.bold())

            Divider()

            VStack(spacing: 12) {
                TextField("E-posta", text: $email)
                    .textFieldStyle(.roundedBorder)
                    .textContentType(.emailAddress)
                    .disableAutocorrection(true)

                SecureField("Şifre", text: $password)
                    .textFieldStyle(.roundedBorder)
                    .textContentType(.password)
                    .onSubmit { submitLogin() }
            }
            .padding(.horizontal, 32)

            if let error = viewModel.loginError {
                Text(error)
                    .font(.caption)
                    .foregroundStyle(.red)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 32)
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
            .padding(.horizontal, 32)
            .disabled(isLoading || email.isEmpty || password.isEmpty)

            Text("Hesabın yok mu? Yöneticinizle iletişime geçin.")
                .font(.caption)
                .foregroundStyle(.secondary)
                .padding(.bottom, 24)
        }
        .frame(width: 380, height: 320)
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
