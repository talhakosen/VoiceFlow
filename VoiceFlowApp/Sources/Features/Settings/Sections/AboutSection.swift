import ComposableArchitecture
import SwiftUI
import AppKit

// MARK: - About

struct AboutSection: View {
    let store: StoreOf<RecordingFeature>

    private var appVersion: String {
        let version = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "0.2"
        let build = Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "0"
        return "\(version) (\(build))"
    }

    var body: some View {
        let state = store.state
        VStack(alignment: .leading, spacing: VFSpacing.xxl) {

            // Uygulama bilgisi
            VFSectionHeader("VoiceFlow")
            VFCard {
                VFRow("Sürüm") {
                    Text("v\(appVersion)").foregroundStyle(.secondary)
                }
                VFRow("Durum", divider: false) {
                    Text(state.statusText).foregroundStyle(.secondary)
                }
            }

            // Servis Yönetimi
            VFSectionHeader("Servis Yönetimi")
            VFCard {
                HStack(spacing: VFSpacing.md) {
                    Button("Servisi Yeniden Başlat") { store.send(.restartBackend) }
                        .buttonStyle(.bordered)
                    Button("Zorla Yeniden Başlat") { store.send(.hardReset) }
                        .buttonStyle(.bordered)
                        .foregroundStyle(VFColor.destructive)
                    Spacer()
                }
                .padding(.horizontal, VFSpacing.xxl)
                .padding(.vertical, VFSpacing.xl)
            }
            VFInfoRow(icon: VFIcon.warning, text: "Zorla yeniden başlatma, arka plan servisini tamamen durdurur ve sıfırdan başlatır.", color: VFColor.warning)
        }
        .padding(VFSpacing.xxxl)
    }
}
