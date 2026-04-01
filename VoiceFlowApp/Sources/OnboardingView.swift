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
        .frame(width: 480, height: 360)
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
        VStack(spacing: 24) {
            Spacer()
            Image(systemName: "waveform.circle.fill")
                .resizable()
                .frame(width: 64, height: 64)
                .foregroundStyle(.blue)

            VStack(spacing: 8) {
                Text("VoiceFlow'a Hoş Geldiniz")
                    .font(.title.bold())
                Text("Sesli dikte — tüm işlem cihazınızda, hiçbir veri dışarı çıkmaz.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            }

            VStack(spacing: 6) {
                HStack(spacing: 8) {
                    Image(systemName: "lock.shield.fill").foregroundStyle(.green)
                    Text("100% Lokal · Açık Kaynak · Kurumsal Hazır")
                        .font(.caption).foregroundStyle(.secondary)
                }
                HStack(spacing: 16) {
                    Label("Kişisel Sözlük", systemImage: "character.book.closed")
                    Label("Sesli Şablonlar", systemImage: "text.badge.plus")
                    Label("Bilgi Tabanı", systemImage: "books.vertical")
                }
                .font(.caption2)
                .foregroundStyle(.secondary)
            }

            Spacer()

            Button("Başlayalım") {
                path.append(.modeSelection)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
        }
        .padding(32)
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
        VStack(alignment: .leading, spacing: 20) {
            Text("Çalışma Modunuzu Seçin")
                .font(.title2.bold())

            VStack(spacing: 8) {
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
        .padding(32)
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
            HStack(spacing: 12) {
                Image(systemName: icon)
                    .frame(width: 28)
                    .foregroundStyle(isSelected ? .white : .secondary)
                VStack(alignment: .leading, spacing: 2) {
                    Text(title).font(.subheadline.bold())
                    Text(description).font(.caption).foregroundStyle(isSelected ? .white.opacity(0.85) : .secondary)
                }
                Spacer()
                if isSelected {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundStyle(.white)
                }
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 10)
            .background(isSelected ? Color.accentColor : Color(nsColor: .controlBackgroundColor))
            .cornerRadius(8)
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Step 3: Accessibility

private struct AccessibilityStep: View {
    let onFinish: () -> Void
    @State private var isGranted = AXIsProcessTrusted()

    var body: some View {
        VStack(spacing: 24) {
            Spacer()
            Image(systemName: isGranted ? "checkmark.shield.fill" : "hand.raised.fill")
                .resizable()
                .scaledToFit()
                .frame(width: 56, height: 56)
                .foregroundStyle(isGranted ? .green : .orange)

            VStack(spacing: 8) {
                Text("Erişilebilirlik İzni")
                    .font(.title2.bold())
                Text(isGranted
                     ? "İzin verildi — otomatik yapıştırma aktif."
                     : "Otomatik yapıştırma için gerekli.\nSistem Ayarları → Gizlilik → Erişilebilirlik → VoiceFlow")
                    .font(.subheadline)
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
        .padding(32)
        .navigationTitle("")
        .onReceive(NotificationCenter.default.publisher(for: NSApplication.didBecomeActiveNotification)) { _ in
            isGranted = AXIsProcessTrusted()
        }
    }
}
