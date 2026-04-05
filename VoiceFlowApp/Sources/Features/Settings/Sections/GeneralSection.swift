import ComposableArchitecture
import SwiftUI
import AppKit

// MARK: - General

struct GeneralSection: View {
    let store: StoreOf<RecordingFeature>
    @AppStorage(AppSettings.deploymentMode) private var deploymentMode = "local"
    @AppStorage(AppSettings.serverURL)      private var serverURL      = "http://127.0.0.1:8765"
    @AppStorage(AppSettings.apiKey)         private var apiKey         = ""
    @State private var showRestartNotice = false

    var body: some View {
        let state = store.state
        VStack(alignment: .leading, spacing: VFSpacing.xxl) {

            // Görünüm
            VFSectionHeader("Görünüm")
            VFCard {
                VFRow("Tema", divider: false) {
                    Picker("", selection: Binding(
                        get: { state.appearanceMode },
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

            // Kısayol
            VFSectionHeader("Kısayol")
            VFCard {
                VFRow("Tuş") {
                    Text("Fn × 2  (kayıt başlat/durdur)").foregroundStyle(.secondary)
                }
                VFRow("Zorla Durdur", divider: false) {
                    Text("⌘S  menü çubuğundan").foregroundStyle(.secondary)
                }
            }

            // Bağlantı
            VFSectionHeader("Bağlantı")
            VFCard {
                VFRow("Dağıtım Modu", divider: deploymentMode == "server") {
                    Picker("", selection: $deploymentMode) {
                        Text("Yerel (Mac)").tag("local")
                        Text("Sunucu (Şirket İçi)").tag("server")
                    }
                    .pickerStyle(.menu)
                    .onChange(of: deploymentMode) { showRestartNotice = true }
                }
                if deploymentMode == "local" {
                    VFRow("", divider: false) {
                        HStack(spacing: 8) {
                            if !state.whisperModelName.isEmpty {
                                Text("Whisper \(state.whisperModelName)")
                                    .font(.caption).foregroundStyle(.tertiary)
                            }
                            if !state.llmAdapterVersion.isEmpty {
                                Text("·").foregroundStyle(.tertiary).font(.caption)
                                Text("Qwen \(state.llmAdapterVersion)")
                                    .font(.caption).foregroundStyle(.tertiary)
                            }
                        }
                    }
                }
                if deploymentMode == "server" {
                    VFRow("Sunucu Adresi") {
                        TextField("https://voiceflow.company.internal:8765", text: $serverURL)
                            .textFieldStyle(.roundedBorder).frame(minWidth: 240)
                    }
                    VFRow("API Anahtarı", divider: false) {
                        SecureField("API anahtarını yapıştırın", text: $apiKey)
                            .textFieldStyle(.roundedBorder).frame(minWidth: 240)
                    }
                }
            }

            if deploymentMode == "server" {
                VFInfoRow(icon: VFIcon.secure, text: "Ses işleme tamamen sunucunuzda gerçekleşir. Hiçbir veri dışarı çıkmaz.", color: VFColor.success)
            }
            if showRestartNotice {
                VFInfoRow(icon: VFIcon.restartCircle, text: "Modu değiştirmek için VoiceFlow'u yeniden başlatın.", color: VFColor.warning)
            }
        }
        .padding(VFSpacing.xxxl)
    }
}
