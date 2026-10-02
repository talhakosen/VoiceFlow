import ComposableArchitecture
import SwiftUI
import AppKit

// MARK: - Recording

struct RecordingSection: View {
    let store: StoreOf<RecordingFeature>
    @AppStorage(AppSettings.llmMode)      private var llmMode      = "local"
    @AppStorage(AppSettings.llmEndpoint)  private var llmEndpoint  = ""
    @AppStorage(AppSettings.trainingMode) private var trainingMode = false
    @State private var showRestartNotice = false

    var body: some View {
        let state = store.state
        VStack(alignment: .leading, spacing: 0) {

            // Banner
            SectionBanner(
                gradient: VFColor.bannerRecFull,
                title: "Kayıt ve Mod Ayarları",
                subtitle: "Genel veya Mühendislik modunu seçin; her mod farklı optimize edilir.",
                iconName: "mic"
            )

        VStack(alignment: .leading, spacing: 28) {
            Spacer().frame(height: 4)

            // MARK: Dil
            SettingsCardSection(title: "Dil") {
                SettingsRow(
                    title: "Transkripsiyon Dili",
                    subtitle: "Konuşacağınız dili seçin; otomatik modda Whisper algılar",
                    isLast: true
                ) {
                    Picker("", selection: Binding(
                        get: { store.state.currentLanguageMode },
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

            // MARK: Mikrofon
            SettingsCardSection(title: "Mikrofon") {
                SettingsRow(
                    title: "Giriş Cihazı",
                    subtitle: "Kayıt sessiz çıkıyorsa buradan başka bir mikrofon seçin. Bluetooth kulaklıklar susturulduğunda sessizce boş ses gönderir.",
                    isLast: true
                ) {
                    Picker("", selection: Binding(
                        get: { store.state.inputDeviceName },
                        set: { store.send(.setInputDevice($0)) }
                    )) {
                        Text("Sistem Varsayılanı").tag("")
                        ForEach(uniqueDevices, id: \.name) { device in
                            Text(device.isDefault ? "\(device.name) (varsayılan)" : device.name)
                                .tag(device.name)
                        }
                    }
                    .pickerStyle(.menu)
                    .frame(width: 220)
                }
            }
            .onAppear { store.send(.loadInputDevices) }

            // MARK: Mod
            SettingsCardSection(title: "Mod") {
                ForEach(Array(AppMode.allCases.enumerated()), id: \.element) { idx, mode in
                    let isLast = idx == AppMode.allCases.count - 1
                    SettingsRow(
                        title: mode.displayName,
                        subtitle: modeSubtitle(mode),
                        isLast: isLast
                    ) {
                        if store.state.currentAppMode == mode {
                            Image(systemName: VFIcon.checkmark)
                                .foregroundStyle(VFColor.primary)
                                .fontWeight(.semibold)
                        }
                    }
                    .contentShape(Rectangle())
                    .onTapGesture { store.send(.selectAppMode(mode)) }
                }
            }

            // MARK: Akıllı Düzeltme
            SettingsCardSection(title: "Akıllı Düzeltme") {
                SettingsRow(
                    title: "Akıllı Düzeltme",
                    subtitle: store.state.currentAppMode == .engineering
                        ? "Engineering modda kapalıdır — teknik terimler korunur"
                        : "Whisper çıktısını LLM ile düzeltir, noktalama ve büyük harf ekler",
                    isLast: store.state.currentAppMode == .engineering
                ) {
                    Toggle("", isOn: Binding(
                        get: { store.state.isCorrectionEnabled },
                        set: { store.send(.setCorrectionEnabled($0)) }
                    ))
                    .labelsHidden()
                    .disabled(store.state.currentAppMode == .engineering)
                }
                if store.state.currentAppMode != .engineering {
                    SettingsRow(
                        title: "Yapay Zeka Motoru",
                        subtitle: llmModeSubtitle(llmMode),
                        isLast: true
                    ) {
                        Picker("", selection: $llmMode) {
                            Text("Yerel").tag("local")
                            Text("RunPod").tag("runpod")
                        }
                        .pickerStyle(.menu)
                        .frame(width: 130)
                        .onChange(of: llmMode) { showRestartNotice = true }
                    }
                }
            }

            // MARK: Kişisel Ses Tanıma
            SettingsCardSection(title: "Kişisel Ses Tanıma") {
                SettingsRow(
                    title: "Ses Tanıma Eğitimi",
                    subtitle: "Her transkripsiyondan sonra düzeltme ekranı görünür; geri bildirimleriniz doğruluğu artırır",
                    isLast: true
                ) {
                    Toggle("", isOn: $trainingMode)
                        .labelsHidden()
                        .onChange(of: trainingMode) { _, val in
                            store.send(.setTrainingMode(val))
                        }
                }
            }

            // Bilgi satırları
            if showRestartNotice {
                InfoNote(icon: VFIcon.restartCircle, text: "Değişikliği uygulamak için servisi yeniden başlatın.", color: VFColor.warning)
            }
            if llmMode == "runpod" {
                InfoNote(icon: VFIcon.bolt, text: "RunPod — GPU ile hızlı transkripsiyon ve düzeltme. İnternet bağlantısı gerektirir.", color: VFColor.warning)
            }

            Spacer()
        }
        .padding(VFSpacing.xxxl)

        } // end outer VStack
    }

    /// Aynı cihaz birden fazla index'te listelenebiliyor (ör. Jabra 0 ve 3);
    /// isimle seçtiğimiz için tekrarları gizliyoruz.
    private var uniqueDevices: [AudioInputDevice] {
        var seen = Set<String>()
        return store.state.availableInputDevices.filter { seen.insert($0.name).inserted }
    }

    private func modeSubtitle(_ mode: AppMode) -> String {
        switch mode {
        case .general:     return "Genel amaçlı; günlük yazışmalar ve notlar için"
        case .engineering: return "Teknik terimler korunur, LLM düzeltme kapalı"
        }
    }

    private func llmModeSubtitle(_ mode: String) -> String {
        switch mode {
        case "local":  return "Qwen 7B bu Mac'te çalışır, internet gerekmez"
        case "runpod": return "RunPod GPU — hızlı transkripsiyon ve düzeltme"
        default:       return ""
        }
    }
}
