import SwiftUI
import AppKit

// MARK: - About

struct AboutSection: View {
    var viewModel: AppViewModel

    private var appVersion: String {
        let version = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "0.2"
        let build = Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "0"
        return "\(version) (\(build))"
    }

    var body: some View {
        VStack(alignment: .leading, spacing: VFSpacing.xxl) {

            // Uygulama bilgisi
            VFSectionHeader("VoiceFlow")
            VFCard {
                VFRow("Sürüm") {
                    Text("v\(appVersion)").foregroundStyle(.secondary)
                }
                VFRow("Durum", divider: false) {
                    Text(viewModel.statusText).foregroundStyle(.secondary)
                }
            }

            // Servis Yönetimi
            VFSectionHeader("Servis Yönetimi")
            VFCard {
                HStack(spacing: VFSpacing.md) {
                    Button("Servisi Yeniden Başlat") { viewModel.restartBackend() }
                        .buttonStyle(.bordered)
                    Button("Zorla Yeniden Başlat") { viewModel.hardReset() }
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
