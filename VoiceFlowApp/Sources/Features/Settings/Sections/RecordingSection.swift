import ComposableArchitecture
import SwiftUI
import AppKit

// MARK: - Recording

struct RecordingSection: View {
    let store: StoreOf<RecordingFeature>
    @AppStorage(AppSettings.llmMode)       private var llmMode       = "local"
    @AppStorage(AppSettings.llmEndpoint)   private var llmEndpoint   = "https://1xb43rk1btwc5p-11434.proxy.runpod.net"
    @AppStorage(AppSettings.trainingMode)  private var trainingMode  = false
    @State private var showRestartNotice = false

    var body: some View {
        let state = store.state
        VStack(alignment: .leading, spacing: VFSpacing.xxl) {

            // Dil
            VFSectionHeader("Dil")
            VFCard {
                VFRow("Dil", divider: false) {
                    Picker("", selection: Binding(
                        get: { state.currentLanguageMode },
                        set: { store.send(.selectLanguageMode($0)) }
                    )) {
                        ForEach(LanguageMode.allCases, id: \.self) { mode in
                            Text(mode.rawValue).tag(mode)
                        }
                    }
                    .pickerStyle(.menu)
                    .frame(width: 160)
                }
            }

            // Bağlam
            VFSectionHeader("Bağlam")
            VFCard {
                VStack(spacing: 0) {
                    ForEach(Array(AppMode.allCases.enumerated()), id: \.element) { idx, mode in
                        VFRow(mode.displayName,
                              divider: idx < AppMode.allCases.count - 1) {
                            if state.currentAppMode == mode {
                                Image(systemName: VFIcon.checkmark)
                                    .foregroundStyle(VFColor.primary)
                                    .fontWeight(.semibold)
                            }
                        }
                        .contentShape(Rectangle())
                        .onTapGesture { store.send(.selectAppMode(mode)) }
                    }
                }
            }
            VFInfoRow(icon: "info.circle", text: "Seçilen alan, düzeltme kalitesini artırmak için bağlamı ayarlar.", color: .secondary)

            // Akıllı Düzeltme
            VFSectionHeader("Akıllı Düzeltme")
            VFCard {
                VFRow("Akıllı Düzeltme",
                      divider: state.currentAppMode != .engineering) {
                    Toggle("", isOn: Binding(
                        get: { state.isCorrectionEnabled },
                        set: { store.send(.setCorrectionEnabled($0)) }
                    ))
                    .labelsHidden()
                    .disabled(state.currentAppMode == .engineering)
                }
                if state.currentAppMode != .engineering {
                    VFRow("Yapay Zeka Motoru", divider: llmMode != "cloud") {
                        Picker("", selection: $llmMode) {
                            Text("Yerel").tag("local")
                            Text("Bulut").tag("cloud")
                            Text("Alibaba").tag("alibaba")
                        }
                        .pickerStyle(.menu)
                        .frame(width: 160)
                        .onChange(of: llmMode) { showRestartNotice = true }
                    }
                    if llmMode == "cloud" {
                        VFRow("Ollama URL", divider: false) {
                            TextField("https://…-11434.proxy.runpod.net", text: $llmEndpoint)
                                .textFieldStyle(.roundedBorder)
                                .frame(minWidth: VFLayout.fieldLarge)
                                .onChange(of: llmEndpoint) { showRestartNotice = true }
                        }
                    }
                }
            }
            if state.currentAppMode == .engineering {
                VFInfoRow(icon: VFIcon.warning, text: "Engineering modda düzeltme kapalıdır — teknik terimler korunur.", color: VFColor.warning)
            }
            if llmMode == "alibaba" {
                VFInfoRow(icon: VFIcon.bolt, text: "Alibaba — Hızlı, yüksek kalite. İnternet gerektirir.", color: VFColor.warning)
            }
            if showRestartNotice {
                VFInfoRow(icon: VFIcon.restartCircle, text: "Değişikliği uygulamak için servisi yeniden başlatın.", color: VFColor.warning)
            }

            // Kişisel Ses Tanıma
            VFSectionHeader("Kişisel Ses Tanıma")
            VFCard {
                VFRow("Ses Tanıma Eğitimi", divider: false) {
                    Toggle("", isOn: $trainingMode)
                        .labelsHidden()
                        .onChange(of: trainingMode) { _, val in
                            store.send(.setTrainingMode(val))
                        }
                }
            }
            VFInfoRow(icon: "info.circle", text: "Her transkripsiyondan sonra geri bildirim ekranı görünür. Düzeltmeleriniz doğruluğu artırır.", color: .secondary)
        }
        .padding(VFSpacing.xxxl)
    }
}
