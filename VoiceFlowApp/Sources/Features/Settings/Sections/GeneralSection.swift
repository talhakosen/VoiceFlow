import ComposableArchitecture
import SwiftUI
import AppKit

// MARK: - GeneralSection

struct GeneralSection: View {
    let store: StoreOf<RecordingFeature>
    @AppStorage(AppSettings.deploymentMode) private var deploymentMode = "local"
    @AppStorage(AppSettings.serverURL)      private var serverURL      = "http://127.0.0.1:8765"
    @AppStorage(AppSettings.apiKey)         private var apiKey         = ""
    @State private var showRestartNotice = false

    var body: some View {
        let state = store.state
        VStack(alignment: .leading, spacing: 28) {

            // Sayfa başlığı
            Text("Genel")
                .font(.system(size: 22, weight: .bold))
                .padding(.bottom, 4)

            // MARK: Görünüm
            SettingsCardSection(title: "Görünüm") {
                SettingsRow(
                    title: "Tema",
                    subtitle: "Uygulama görünümünü tercih ettiğiniz renge göre ayarlayın"
                ) {
                    Picker("", selection: Binding(
                        get: { store.state.appearanceMode },
                        set: { store.send(.setAppearanceMode($0)) }
                    )) {
                        ForEach(AppearanceMode.allCases, id: \.self) { mode in
                            Text(mode.displayName).tag(mode)
                        }
                    }
                    .pickerStyle(.segmented)
                    .frame(width: 200)
                }
            }

            // MARK: Kısayol
            SettingsCardSection(title: "Kısayol") {
                SettingsRow(
                    title: "Kayıt Başlat / Durdur",
                    subtitle: "Fn tuşuna iki kez basarak kayıt başlatın veya durdurun",
                    isLast: false
                ) {
                    Text("Fn × 2")
                        .font(.system(size: 13, weight: .medium))
                        .foregroundStyle(.secondary)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 4)
                        .background(Color.primary.opacity(0.07))
                        .clipShape(RoundedRectangle(cornerRadius: 6))
                }
                SettingsRow(
                    title: "Zorla Durdur",
                    subtitle: "Kayıt takılı kalırsa menü çubuğundan durdurabilirsiniz",
                    isLast: true
                ) {
                    Text("Menü çubuğu")
                        .font(.system(size: 13, weight: .medium))
                        .foregroundStyle(.secondary)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 4)
                        .background(Color.primary.opacity(0.07))
                        .clipShape(RoundedRectangle(cornerRadius: 6))
                }
            }

            // MARK: Bağlantı
            SettingsCardSection(title: "Bağlantı") {
                SettingsRow(
                    title: "Dağıtım Modu",
                    subtitle: deploymentMode == "local"
                        ? "Ses işleme bu Mac'te gerçekleşir"
                        : "Ses işleme şirket sunucusunda gerçekleşir",
                    isLast: deploymentMode == "local"
                ) {
                    Picker("", selection: $deploymentMode) {
                        Text("Yerel (Mac)").tag("local")
                        Text("Sunucu").tag("server")
                    }
                    .pickerStyle(.menu)
                    .frame(width: 140)
                    .onChange(of: deploymentMode) { showRestartNotice = true }
                }

                if deploymentMode == "local" && (!state.whisperModelName.isEmpty || !state.llmAdapterVersion.isEmpty) {
                    HStack(spacing: 6) {
                        if !state.whisperModelName.isEmpty {
                            Label(state.whisperModelName, systemImage: "waveform")
                                .font(.caption2).foregroundStyle(.tertiary)
                        }
                        if !state.llmAdapterVersion.isEmpty {
                            Text("·").foregroundStyle(.quaternary).font(.caption2)
                            Label(state.llmAdapterVersion, systemImage: "cpu")
                                .font(.caption2).foregroundStyle(.tertiary)
                        }
                    }
                    .padding(.horizontal, 16)
                    .padding(.bottom, 12)
                }

                if deploymentMode == "server" {
                    SettingsRow(title: "Sunucu Adresi", subtitle: "Şirket içi VoiceFlow sunucusunun adresi", isLast: false) {
                        TextField("https://voiceflow.şirket.internal:8765", text: $serverURL)
                            .textFieldStyle(.roundedBorder)
                            .frame(minWidth: 220)
                    }
                    SettingsRow(title: "API Anahtarı", subtitle: "Sunucunuzdan aldığınız erişim anahtarı", isLast: true) {
                        SecureField("API anahtarını yapıştırın", text: $apiKey)
                            .textFieldStyle(.roundedBorder)
                            .frame(minWidth: 220)
                    }
                }
            }

            // Bilgi satırları
            if deploymentMode == "server" {
                HStack(spacing: 8) {
                    Image(systemName: VFIcon.secure).foregroundStyle(VFColor.success)
                    Text("Ses işleme tamamen sunucunuzda gerçekleşir. Hiçbir veri dışarı çıkmaz.")
                        .font(.caption).foregroundStyle(.secondary)
                }
                .padding(.horizontal, 4)
                .padding(.top, -8)
            }

            if showRestartNotice {
                HStack(spacing: 8) {
                    Image(systemName: VFIcon.restartCircle).foregroundStyle(VFColor.warning)
                    Text("Modu değiştirmek için VoiceFlow'u yeniden başlatın.")
                        .font(.caption).foregroundStyle(.secondary)
                }
                .padding(.horizontal, 4)
                .padding(.top, -8)
            }

            Spacer()
        }
        .padding(VFSpacing.xxxl)
    }
}

// MARK: - Shared Section Card Components

/// Başlıklı kart grubu — Settings içerik alanında kullanılır.
struct SettingsCardSection<Content: View>: View {
    let title: String
    @ViewBuilder let content: () -> Content

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.system(size: 12, weight: .semibold))
                .foregroundStyle(.secondary)
                .textCase(.uppercase)
                .tracking(0.5)
                .padding(.horizontal, 4)

            VStack(spacing: 0) {
                content()
            }
            .background(Color(nsColor: .controlBackgroundColor))
            .clipShape(RoundedRectangle(cornerRadius: VFRadius.lg))
            .overlay(
                RoundedRectangle(cornerRadius: VFRadius.lg)
                    .strokeBorder(Color.primary.opacity(0.07), lineWidth: 1)
            )
        }
    }
}

/// Kart içi satır — başlık + alt başlık + sağ kontrol.
struct SettingsRow<Trailing: View>: View {
    let title: String
    var subtitle: String? = nil
    var isLast: Bool = true
    @ViewBuilder let trailing: () -> Trailing

    var body: some View {
        VStack(spacing: 0) {
            HStack(alignment: .center, spacing: 16) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(title)
                        .font(.system(size: 13, weight: .medium))
                        .foregroundStyle(.primary)
                    if let sub = subtitle {
                        Text(sub)
                            .font(.system(size: 11))
                            .foregroundStyle(.tertiary)
                            .lineLimit(2)
                    }
                }
                Spacer(minLength: 12)
                trailing()
            }
            .padding(.horizontal, 16)
            .padding(.vertical, subtitle != nil ? 12 : 11)

            if !isLast {
                Divider().padding(.leading, 16)
            }
        }
    }
}
