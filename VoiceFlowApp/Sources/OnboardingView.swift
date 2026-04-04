import SwiftUI

private enum OnboardingStep: Hashable {
    case modeSelection
    case accessibility
}

struct OnboardingView: View {
    var onComplete: (() -> Void)? = nil

    @AppStorage(AppSettings.appMode)            private var appMode = "general"
    @AppStorage(AppSettings.defaultLanguage)    private var defaultLanguage = LanguageMode.turkish.rawValue
    @AppStorage(AppSettings.onboardingComplete) private var onboardingComplete = false

    @State private var path: [OnboardingStep] = []

    var body: some View {
        NavigationStack(path: $path) {
            WelcomeStep(path: $path)
                .navigationDestination(for: OnboardingStep.self) { step in
                    switch step {
                    case .modeSelection:
                        ModeSelectionStep(
                            appMode: $appMode,
                            defaultLanguage: $defaultLanguage,
                            path: $path
                        )
                    case .accessibility:
                        AccessibilityStep(onFinish: finish)
                    }
                }
        }
        .frame(width: VFLayout.WindowSize.onboarding.width, height: VFLayout.WindowSize.onboarding.height)
    }

    private func finish() {
        onboardingComplete = true
        onComplete?()
    }
}

// MARK: - Step 1: Welcome

private struct WelcomeStep: View {
    @Binding var path: [OnboardingStep]

    var body: some View {
        VStack(spacing: VFSpacing.huge) {
            Spacer()
            Image(systemName: VFIcon.appLogoFill)
                .resizable()
                .frame(width: VFLayout.onboardingIconSize, height: VFLayout.onboardingIconSize)
                .foregroundStyle(VFColor.primary)

            VStack(spacing: VFSpacing.md) {
                Text("VoiceFlow'a Hoş Geldiniz")
                    .font(VFFont.title)
                Text("Sesli dikte — tüm işlem cihazınızda, hiçbir veri dışarı çıkmaz.")
                    .font(VFFont.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            }

            VStack(spacing: VFSpacing.sm) {
                HStack(spacing: VFSpacing.md) {
                    Image(systemName: VFIcon.secureFill).foregroundStyle(VFColor.success)
                    Text("100% Lokal · Açık Kaynak · Kurumsal Hazır")
                        .font(VFFont.caption).foregroundStyle(.secondary)
                }
                HStack(spacing: VFSpacing.xxl) {
                    Label("Kişisel Sözlük", systemImage: VFIcon.dictionary)
                    Label("Sesli Şablonlar", systemImage: VFIcon.snippets)
                    Label("Bilgi Tabanı",   systemImage: VFIcon.knowledgeBase)
                }
                .font(VFFont.caption2)
                .foregroundStyle(.secondary)
            }

            Spacer()

            Button("Başlayalım") {
                path.append(.modeSelection)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
        }
        .padding(VFSpacing.max)
        .navigationTitle("")
    }
}

// MARK: - Step 2: Mode + Language

private struct ModeSelectionStep: View {
    @Binding var appMode: String
    @Binding var defaultLanguage: String
    @Binding var path: [OnboardingStep]

    private let modes: [(id: String, title: String, description: String, icon: String)] = [
        ("general",     "Genel",        "Günlük Türkçe dikte — karakter düzeltmeli",        "text.bubble"),
        ("engineering", "Mühendislik", "Teknik terimler korunur, kod isimleri değişmez",    "chevron.left.forwardslash.chevron.right"),
        ("office",      "Ofis",        "Resmi dil, kısaltma açma, iş yazışması tonu",       "envelope"),
    ]

    var body: some View {
        VStack(alignment: .leading, spacing: VFSpacing.xxxl) {
            Text("Çalışma Modunuzu Seçin")
                .font(VFFont.title2)

            VStack(spacing: VFSpacing.md) {
                ForEach(modes, id: \.id) { m in
                    ModeRow(
                        icon: m.icon,
                        title: m.title,
                        description: m.description,
                        isSelected: appMode == m.id,
                        onSelect: { appMode = m.id }
                    )
                }
            }

            Divider()

            HStack {
                Text("Dil:")
                    .font(.subheadline)
                Picker("", selection: $defaultLanguage) {
                    ForEach(LanguageMode.allCases, id: \.self) { mode in
                        Text(mode.rawValue).tag(mode.rawValue)
                    }
                }
                .pickerStyle(.segmented)
                .frame(maxWidth: 300)
            }

            HStack(spacing: 6) {
                Image(systemName: "gearshape").foregroundStyle(.secondary)
                Text("Dil, mod ve yapay zeka düzeltme ayarlarını dilediğiniz zaman Ayarlar'dan değiştirebilirsiniz.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            HStack {
                Spacer()
                Button("Devam") {
                    path.append(.accessibility)
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.large)
            }
        }
        .padding(VFSpacing.max)
        .navigationTitle("")
    }
}

private struct ModeRow: View {
    let icon: String
    let title: String
    let description: String
    let isSelected: Bool
    let onSelect: () -> Void

    var body: some View {
        Button(action: onSelect) {
            HStack(spacing: VFSpacing.xl) {
                Image(systemName: icon)
                    .frame(width: 28)
                    .foregroundStyle(isSelected ? .white : .secondary)
                VStack(alignment: .leading, spacing: VFSpacing.xxs) {
                    Text(title).font(VFFont.subheadline.bold())
                    Text(description).font(VFFont.caption)
                        .foregroundStyle(isSelected ? .white.opacity(0.85) : .secondary)
                }
                Spacer()
                if isSelected {
                    Image(systemName: VFIcon.checkFill)
                        .foregroundStyle(.white)
                }
            }
            .padding(.horizontal, 14)
            .padding(.vertical, VFSpacing.lg)
            .background(isSelected ? VFColor.primary : Color(nsColor: .controlBackgroundColor))
            .cornerRadius(VFRadius.md)
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Step 3: Accessibility

private struct AccessibilityStep: View {
    let onFinish: () -> Void
    @State private var isGranted = AXIsProcessTrusted()

    var body: some View {
        VStack(spacing: VFSpacing.huge) {
            Spacer()
            Image(systemName: isGranted ? "checkmark.shield.fill" : "hand.raised.fill")
                .resizable()
                .scaledToFit()
                .frame(width: 56, height: 56)
                .foregroundStyle(isGranted ? VFColor.success : VFColor.warning)

            VStack(spacing: VFSpacing.md) {
                Text("Erişilebilirlik İzni")
                    .font(VFFont.title2)
                Text(isGranted
                     ? "İzin verildi — otomatik yapıştırma aktif."
                     : "Otomatik yapıştırma için gerekli.\nSistem Ayarları → Gizlilik → Erişilebilirlik → VoiceFlow")
                    .font(VFFont.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            }

            if !isGranted {
                Button("Sistem Ayarlarını Aç") {
                    if let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility") {
                        NSWorkspace.shared.open(url)
                    }
                }
                .buttonStyle(.bordered)
            }

            Spacer()

            Button(isGranted ? "Başla" : "Atla ve Başla") {
                onFinish()
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
        }
        .padding(VFSpacing.max)
        .navigationTitle("")
        .onReceive(NotificationCenter.default.publisher(for: NSApplication.didBecomeActiveNotification)) { _ in
            isGranted = AXIsProcessTrusted()
        }
    }
}
