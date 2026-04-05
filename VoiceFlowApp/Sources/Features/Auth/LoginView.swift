import ComposableArchitecture
import SwiftUI

struct LoginView: View {
    let store: StoreOf<AuthFeature>

    var body: some View {
        let state = store.state
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
                TextField("E-posta", text: Binding(
                    get: { state.email },
                    set: { store.send(.emailChanged($0)) }
                ))
                .textFieldStyle(.roundedBorder)
                .textContentType(.emailAddress)
                .disableAutocorrection(true)

                SecureField("Şifre", text: Binding(
                    get: { state.password },
                    set: { store.send(.passwordChanged($0)) }
                ))
                .textFieldStyle(.roundedBorder)
                .textContentType(.password)
                .onSubmit { store.send(.loginTapped) }
            }
            .padding(.horizontal, VFSpacing.max)

            if let error = state.loginError {
                Text(error)
                    .font(VFFont.caption)
                    .foregroundStyle(VFColor.destructive)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, VFSpacing.max)
            }

            Button(action: { store.send(.loginTapped) }) {
                ZStack {
                    if state.isLoading {
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
            .disabled(state.isLoading || state.email.isEmpty || state.password.isEmpty)

            Text("Hesabın yok mu? Yöneticinizle iletişime geçin.")
                .font(VFFont.caption)
                .foregroundStyle(.secondary)
                .padding(.bottom, VFSpacing.huge)
        }
        .frame(width: VFLayout.WindowSize.login.width, height: VFLayout.WindowSize.login.height)
    }
}
