import ComposableArchitecture
import SwiftUI
import AppKit

// MARK: - About

struct AboutSection: View {
    let store: StoreOf<RecordingFeature>

    private var appVersion: String {
        let version = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "0.2"
        let build   = Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "0"
        return "\(version) (\(build))"
    }

    var body: some View {
        let state = store.state
        VStack(alignment: .leading, spacing: 28) {

            Text("Hakkında")
                .font(.system(size: 22, weight: .bold))
                .padding(.bottom, 4)

            // Uygulama Bilgisi
            SettingsCardSection(title: "Uygulama") {
                SettingsRow(title: "VoiceFlow", subtitle: "Gerçek zamanlı konuşma tanıma — macOS", isLast: false) {
                    Text("v\(appVersion)")
                        .font(.system(size: 13, weight: .medium))
                        .foregroundStyle(.secondary)
                }
                SettingsRow(title: "Durum", subtitle: "Anlık servis ve model durumu", isLast: false) {
                    Text(state.statusText)
                        .foregroundStyle(.secondary)
                        .font(.system(size: 13))
                }
                SettingsRow(title: "Whisper Modeli", subtitle: "Ses tanıma motoru", isLast: state.llmAdapterVersion.isEmpty) {
                    Text(state.whisperModelName.isEmpty ? "—" : state.whisperModelName)
                        .foregroundStyle(.secondary)
                        .font(.system(size: 13))
                }
                if !state.llmAdapterVersion.isEmpty {
                    SettingsRow(title: "LLM Adaptörü", subtitle: "Akıllı düzeltme motoru", isLast: true) {
                        Text(state.llmAdapterVersion)
                            .foregroundStyle(.secondary)
                            .font(.system(size: 13))
                    }
                }
            }

            // Servis Yönetimi
            SettingsCardSection(title: "Servis Yönetimi") {
                HStack(spacing: 12) {
                    Button("Servisi Yeniden Başlat") {
                        store.send(.restartBackend)
                    }
                    .buttonStyle(.bordered)

                    Button("Zorla Yeniden Başlat") {
                        store.send(.hardReset)
                    }
                    .buttonStyle(.bordered)
                    .foregroundStyle(VFColor.destructive)

                    Spacer()
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 14)
            }

            InfoNote(icon: VFIcon.warning, text: "Zorla yeniden başlatma arka plan servisini tamamen durdurur ve sıfırdan başlatır. Devam eden kayıt iptal edilir.", color: VFColor.warning)

            Spacer()
        }
        .padding(VFSpacing.xxxl)
    }
}
