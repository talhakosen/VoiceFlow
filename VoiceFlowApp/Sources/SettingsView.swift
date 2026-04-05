import SwiftUI
import AppKit

// MARK: - Window access helper

private struct HostingWindowFinder: NSViewRepresentable {
    var callback: (NSWindow?) -> Void
    func makeNSView(context: Context) -> NSView {
        let view = NSView()
        DispatchQueue.main.async { self.callback(view.window) }
        return view
    }
    func updateNSView(_ nsView: NSView, context: Context) {}
}

private extension View {
    func withHostingWindowCallback(_ callback: @escaping (NSWindow?) -> Void) -> some View {
        background(HostingWindowFinder(callback: callback))
    }
}

// MARK: - Settings Section

private enum SettingsSection: String, CaseIterable, Identifiable {
    case general       = "Genel"
    case recording     = "Kayıt"
    case dictionary    = "Sözlük"
    case snippets      = "Şablonlar"
    case knowledgeBase = "Bilgi Tabanı"
    case account       = "Hesap"
    case about         = "Hakkında"

    var id: String { rawValue }

    var icon: String {
        switch self {
        case .general:       return VFIcon.settings
        case .recording:     return VFIcon.recording
        case .dictionary:    return VFIcon.dictionary
        case .snippets:      return VFIcon.snippets
        case .knowledgeBase: return VFIcon.knowledgeBase
        case .account:       return VFIcon.account
        case .about:         return VFIcon.about
        }
    }
}

// MARK: - SettingsView (custom 2-panel — icon strip on collapse)

struct SettingsView: View {
    var viewModel: AppViewModel
    var settingsVM: SettingsViewModel

    @State private var selectedSection: SettingsSection = .general
    @State private var sidebarCollapsed = false

    // Traffic lights macOS'ta ~x:12, genişlik ~52pt. Collapse butonu hemen sağında.
    private let trafficLightsWidth: CGFloat = 72
    private let toolbarHeight: CGFloat = 44

    var body: some View {
        VStack(spacing: 0) {

            // MARK: Toolbar row — tüm genişlik, sidebar ile aynı arka plan
            HStack(alignment: .center, spacing: 0) {
                Spacer().frame(width: trafficLightsWidth)
                Button {
                    withAnimation(VFAnimation.standard) { sidebarCollapsed.toggle() }
                } label: {
                    Image(systemName: sidebarCollapsed ? "sidebar.right" : "sidebar.left")
                        .font(.system(size: 13))
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
                .help(sidebarCollapsed ? "Navigasyonu Genişlet" : "Navigasyonu Daralt")

                Spacer()

                Button { selectedSection = .account } label: {
                    Image(systemName: "person.circle")
                        .font(.system(size: 15))
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
                .help("Hesap")
                .padding(.trailing, 16)
            }
            .padding(.top, 8)
            .padding(.bottom, 8)
            .background(Color(nsColor: .windowBackgroundColor))

            // MARK: Ana alan
            HStack(spacing: 0) {

                // Sidebar
                VStack(alignment: .leading, spacing: 0) {
                    // Logo header — toolbar'ın hemen altında
                    HStack(spacing: 8) {
                        Image(systemName: VFIcon.appLogo)
                            .font(.system(size: 18, weight: .semibold))
                        if !sidebarCollapsed {
                            Text("VoiceFlow")
                                .font(.system(size: 16, weight: .bold))
                                .transition(.opacity.combined(with: .move(edge: .leading)))
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: sidebarCollapsed ? .center : .leading)
                    .padding(.horizontal, sidebarCollapsed ? 0 : 20)
                    .padding(.vertical, 16)

                    // Nav items
                    VStack(spacing: 2) {
                        ForEach(SettingsSection.allCases) { section in
                            SidebarNavItem(
                                section: section,
                                isSelected: selectedSection == section,
                                collapsed: sidebarCollapsed
                            ) { selectedSection = section }
                        }
                    }
                    .padding(.horizontal, 10)

                    Spacer()
                }
                .frame(width: sidebarCollapsed ? VFLayout.sidebarCollapsedWidth : VFLayout.sidebarWidth)
                .background(Color(nsColor: .windowBackgroundColor))
                .animation(VFAnimation.standard, value: sidebarCollapsed)

                // Content card
                ScrollView {
                    Group {
                        switch selectedSection {
                        case .general:       GeneralSection(viewModel: viewModel)
                        case .recording:     RecordingSection(viewModel: viewModel)
                        case .dictionary:    DictionarySection(settingsVM: settingsVM)
                        case .snippets:      SnippetsSection(settingsVM: settingsVM)
                        case .knowledgeBase: KnowledgeBaseSection(settingsVM: settingsVM)
                        case .account:       AccountSection(settingsVM: settingsVM, viewModel: viewModel)
                        case .about:         AboutSection(viewModel: viewModel)
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .topLeading)
                }
                .background(Color(nsColor: .controlBackgroundColor))
                .clipShape(RoundedRectangle(cornerRadius: 12))
                .shadow(color: .black.opacity(0.06), radius: 6, x: 0, y: 2)
                .padding(.trailing, 8)
                .padding(.bottom, 8)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
            .background(Color(nsColor: .windowBackgroundColor))
        }
        .frame(width: VFLayout.WindowSize.settings.width, height: VFLayout.WindowSize.settings.height)
        .background(Color(nsColor: .windowBackgroundColor))
        .ignoresSafeArea(.all)
        .onDisappear {
            viewModel.itDatasetActive = false
            viewModel.itDatasetCurrentIndex = -1
        }
    }
}

// MARK: - SidebarNavItem

private struct SidebarNavItem: View {
    let section: SettingsSection
    let isSelected: Bool
    let collapsed: Bool
    let onTap: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: onTap) {
            HStack(spacing: 12) {
                Image(systemName: section.icon)
                    .font(.system(size: 18, weight: .regular))
                    .frame(width: 22, height: 22)
                    .foregroundStyle(isSelected ? Color.primary : Color.secondary)

                if !collapsed {
                    Text(section.rawValue)
                        .font(.system(size: 15, weight: isSelected ? .semibold : .regular))
                        .foregroundStyle(isSelected ? Color.primary : Color.secondary)
                        .transition(.opacity.combined(with: .move(edge: .leading)))
                }
            }
            .frame(maxWidth: .infinity, alignment: collapsed ? .center : .leading)
            .padding(.horizontal, collapsed ? 8 : 12)
            .padding(.vertical, 10)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(isSelected
                          ? Color.primary.opacity(0.10)
                          : isHovered ? Color.primary.opacity(0.05) : Color.clear)
            )
        }
        .buttonStyle(.plain)
        .onHover { isHovered = $0 }
        .help(collapsed ? section.rawValue : "")
    }
}

// MARK: - Shared Settings UI Components

/// Yuvarlak köşeli kart — section içeriğini sarar.
private struct VFCard<Content: View>: View {
    @ViewBuilder var content: () -> Content
    var body: some View {
        VStack(spacing: 0) { content() }
            .background(Color(nsColor: .controlBackgroundColor))
            .clipShape(RoundedRectangle(cornerRadius: VFRadius.lg))
    }
}

/// Section başlığı — bold, birincil renk.
private struct VFSectionHeader: View {
    let title: String
    init(_ title: String) { self.title = title }
    var body: some View {
        Text(title)
            .font(.system(size: 13, weight: .semibold))
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.horizontal, VFSpacing.xs)
    }
}

/// Label + trailing content satırı. Sonuncu satırda `divider: false` ver.
private struct VFRow<Trailing: View>: View {
    let label: String
    let divider: Bool
    @ViewBuilder var trailing: () -> Trailing

    init(_ label: String, divider: Bool = true, @ViewBuilder trailing: @escaping () -> Trailing) {
        self.label = label
        self.divider = divider
        self.trailing = trailing
    }

    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: VFSpacing.xxl) {
                Text(label).font(VFFont.body)
                Spacer(minLength: VFSpacing.xl)
                trailing()
            }
            .padding(.horizontal, VFSpacing.xxl)
            .padding(.vertical, VFSpacing.xl)
            if divider {
                Divider().padding(.leading, VFSpacing.xxl)
            }
        }
    }
}

/// Info satırı — icon + caption metin.
private struct VFInfoRow: View {
    let icon: String
    let text: String
    let color: Color
    var body: some View {
        HStack(spacing: VFSpacing.sm) {
            Image(systemName: icon).foregroundStyle(color)
            Text(text).font(VFFont.caption).foregroundStyle(.secondary)
        }
        .padding(.horizontal, VFSpacing.xs)
    }
}

// MARK: - General

private struct GeneralSection: View {
    var viewModel: AppViewModel
    @AppStorage(AppSettings.deploymentMode) private var deploymentMode = "local"
    @AppStorage(AppSettings.serverURL)      private var serverURL      = "http://127.0.0.1:8765"
    @AppStorage(AppSettings.apiKey)         private var apiKey         = ""
    @State private var showRestartNotice = false

    var body: some View {
        VStack(alignment: .leading, spacing: VFSpacing.xxl) {

            // Görünüm
            VFSectionHeader("Görünüm")
            VFCard {
                VFRow("Tema", divider: false) {
                    Picker("", selection: Binding(
                        get: { viewModel.appearanceMode },
                        set: { viewModel.appearanceMode = $0 }
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
                            if !viewModel.whisperModelName.isEmpty {
                                Text("Whisper \(viewModel.whisperModelName)")
                                    .font(.caption).foregroundStyle(.tertiary)
                            }
                            if !viewModel.llmAdapterVersion.isEmpty {
                                Text("·").foregroundStyle(.tertiary).font(.caption)
                                Text("Qwen \(viewModel.llmAdapterVersion)")
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

// MARK: - Dictionary

private struct DictionarySection: View {
    var settingsVM: SettingsViewModel

    @State private var selectedTab = 0
    @State private var newTrigger = ""
    @State private var newReplacement = ""

    private var personalEntries: [DictionaryEntry] {
        settingsVM.dictionaryEntries.filter { $0.scope == "personal" }
    }

    private var teamEntries: [DictionaryEntry] {
        settingsVM.dictionaryEntries.filter { $0.scope == "team" }
    }

    private func isSharedWithTeam(_ entry: DictionaryEntry) -> Bool {
        teamEntries.contains { $0.trigger == entry.trigger && $0.replacement == entry.replacement }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: VFSpacing.xxl) {

            // Tab
            Picker("", selection: $selectedTab) {
                Text("Kişisel (\(personalEntries.count))").tag(0)
                Text("Takım (\(teamEntries.count))").tag(1)
            }
            .pickerStyle(.segmented)
            .frame(width: 260, alignment: .leading)

            // Liste
            VFSectionHeader(selectedTab == 0 ? "Kişisel Kurallar" : "Takım Kuralları")
            VFCard {
                let entries = selectedTab == 0 ? personalEntries : teamEntries
                if entries.isEmpty {
                    Text(selectedTab == 0
                         ? "Henüz kişisel kural yok."
                         : "Takım kuralı yok. Kişisel kurallarını takıma ekleyebilirsin.")
                        .foregroundStyle(.secondary)
                        .font(VFFont.body)
                        .padding(.horizontal, VFSpacing.xxl)
                        .padding(.vertical, VFSpacing.xl)
                } else {
                    ForEach(Array(entries.enumerated()), id: \.element.id) { idx, entry in
                        DictionaryRow(
                            entry: entry,
                            alreadyShared: selectedTab == 0 ? isSharedWithTeam(entry) : false,
                            onDelete: { settingsVM.deleteDictionaryEntry(id: entry.id) },
                            onShareToTeam: selectedTab == 0 ? {
                                settingsVM.addDictionaryEntry(
                                    trigger: entry.trigger,
                                    replacement: entry.replacement,
                                    scope: "team"
                                )
                            } : nil
                        )
                        if idx < entries.count - 1 {
                            Divider().padding(.leading, VFSpacing.xxl)
                        }
                    }
                }
            }

            // Kural Ekle
            VFSectionHeader(selectedTab == 0 ? "Kişisel Kural Ekle" : "Takım Kuralı Ekle")
            VFCard {
                VStack(spacing: 0) {
                    HStack(spacing: VFSpacing.md) {
                        TextField("kelime (örn: voisflow)", text: $newTrigger)
                            .textFieldStyle(.roundedBorder)
                        Image(systemName: VFIcon.arrow).foregroundStyle(.secondary)
                        TextField("doğru yazım (örn: VoiceFlow)", text: $newReplacement)
                            .textFieldStyle(.roundedBorder)
                        Button("Ekle") {
                            guard !newTrigger.isEmpty, !newReplacement.isEmpty else { return }
                            let scope = selectedTab == 0 ? "personal" : "team"
                            settingsVM.addDictionaryEntry(trigger: newTrigger, replacement: newReplacement, scope: scope)
                            newTrigger = ""
                            newReplacement = ""
                        }
                        .buttonStyle(.borderedProminent)
                        .disabled(newTrigger.isEmpty || newReplacement.isEmpty)
                    }
                    .padding(.horizontal, VFSpacing.xxl)
                    .padding(.vertical, VFSpacing.xl)
                }
            }
            VFInfoRow(icon: "info.circle", text: "Whisper sonrası, düzeltme öncesi uygulanır. Büyük/küçük harf duyarsız, kelime sınırı korunur.", color: .secondary)
        }
        .padding(VFSpacing.xxxl)
        .onAppear { settingsVM.loadDictionary() }
    }
}

private struct DictionaryRow: View {
    let entry: DictionaryEntry
    let alreadyShared: Bool
    let onDelete: () -> Void
    let onShareToTeam: (() -> Void)?

    var body: some View {
        HStack(spacing: VFSpacing.md) {
            Text(entry.trigger)
                .frame(minWidth: VFLayout.fieldSmall, alignment: .leading)
                .foregroundStyle(.primary)
                .font(VFFont.body)
            Image(systemName: VFIcon.arrow)
                .foregroundStyle(.secondary)
                .font(VFFont.caption)
            Text(entry.replacement)
                .frame(maxWidth: .infinity, alignment: .leading)
                .foregroundStyle(.primary)
                .font(VFFont.body)

            if let share = onShareToTeam {
                Button {
                    share()
                } label: {
                    Label(
                        alreadyShared ? "Eklendi" : "Takıma ekle",
                        systemImage: alreadyShared ? VFIcon.checkmark : VFIcon.shareTeam
                    )
                    .font(VFFont.caption)
                    .foregroundStyle(alreadyShared ? Color.secondary : VFColor.primary)
                }
                .buttonStyle(.plain)
                .disabled(alreadyShared)
            }

            Button { onDelete() } label: {
                Image(systemName: VFIcon.delete).foregroundStyle(VFColor.destructive)
            }
            .buttonStyle(.plain)
        }
        .padding(.horizontal, VFSpacing.xxl)
        .padding(.vertical, VFSpacing.xl)
    }
}

// MARK: - Snippets

private struct SnippetsSection: View {
    var settingsVM: SettingsViewModel

    @State private var newTrigger = ""
    @State private var newExpansion = ""
    @State private var newScope = "personal"

    var body: some View {
        VStack(alignment: .leading, spacing: VFSpacing.xxl) {

            VFSectionHeader("Şablon Listesi")
            VFCard {
                if settingsVM.snippetEntries.isEmpty {
                    Text("Henüz şablon yok. Ses kaydında tetikleyici söyleyince şablon yapıştırılır.")
                        .foregroundStyle(.secondary)
                        .font(VFFont.body)
                        .padding(.horizontal, VFSpacing.xxl)
                        .padding(.vertical, VFSpacing.xl)
                } else {
                    ForEach(Array(settingsVM.snippetEntries.enumerated()), id: \.element.id) { idx, entry in
                        HStack(spacing: VFSpacing.md) {
                            Text(entry.triggerPhrase)
                                .frame(minWidth: VFLayout.fieldSmall, alignment: .leading)
                                .font(VFFont.body)
                            Image(systemName: VFIcon.arrow).foregroundStyle(.secondary)
                            Text(entry.expansion)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .lineLimit(2)
                                .font(VFFont.body)
                            Text(entry.scope == "personal" ? "Kişisel" : "Takım")
                                .font(VFFont.caption)
                                .foregroundStyle(.secondary)
                                .frame(width: 60)
                            if entry.scope == "personal" {
                                Button {
                                    settingsVM.deleteSnippet(id: entry.id)
                                } label: {
                                    Image(systemName: VFIcon.delete).foregroundStyle(VFColor.destructive)
                                }
                                .buttonStyle(.plain)
                            }
                        }
                        .padding(.horizontal, VFSpacing.xxl)
                        .padding(.vertical, VFSpacing.xl)
                        if idx < settingsVM.snippetEntries.count - 1 {
                            Divider().padding(.leading, VFSpacing.xxl)
                        }
                    }
                }
            }

            VFSectionHeader("Şablon Ekle")
            VFCard {
                VStack(spacing: 0) {
                    HStack(spacing: VFSpacing.md) {
                        TextField("tetikleyici (örn: standart imza)", text: $newTrigger)
                            .textFieldStyle(.roundedBorder)
                        Image(systemName: VFIcon.arrow).foregroundStyle(.secondary)
                        TextField("içerik (açılacak metin)", text: $newExpansion)
                            .textFieldStyle(.roundedBorder)
                        Picker("", selection: $newScope) {
                            Text("Kişisel").tag("personal")
                            Text("Takım").tag("team")
                        }
                        .frame(width: 90)
                        Button("Ekle") {
                            guard !newTrigger.isEmpty, !newExpansion.isEmpty else { return }
                            settingsVM.addSnippet(triggerPhrase: newTrigger, expansion: newExpansion, scope: newScope)
                            newTrigger = ""
                            newExpansion = ""
                        }
                        .buttonStyle(.borderedProminent)
                        .disabled(newTrigger.isEmpty || newExpansion.isEmpty)
                    }
                    .padding(.horizontal, VFSpacing.xxl)
                    .padding(.vertical, VFSpacing.xl)
                }
            }
            VFInfoRow(icon: "info.circle", text: "Tetikleyici kelime sesi tam eşleştiğinde şablon metnini yapıştırır. Sözlükten sonra, düzeltmeden önce uygulanır.", color: .secondary)
        }
        .padding(VFSpacing.xxxl)
        .onAppear { settingsVM.loadSnippets() }
    }
}

// MARK: - Recording

private struct RecordingSection: View {
    var viewModel: AppViewModel
    @AppStorage(AppSettings.llmMode)       private var llmMode       = "local"
    @AppStorage(AppSettings.llmEndpoint)   private var llmEndpoint   = "https://1xb43rk1btwc5p-11434.proxy.runpod.net"
    @AppStorage(AppSettings.trainingMode)  private var trainingMode  = false
    @State private var showRestartNotice = false

    var body: some View {
        VStack(alignment: .leading, spacing: VFSpacing.xxl) {

            // Dil
            VFSectionHeader("Dil")
            VFCard {
                VFRow("Dil", divider: false) {
                    Picker("", selection: Binding(
                        get: { viewModel.currentLanguageMode },
                        set: { viewModel.selectLanguageMode($0) }
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
                            if viewModel.currentAppMode == mode {
                                Image(systemName: VFIcon.checkmark)
                                    .foregroundStyle(VFColor.primary)
                                    .fontWeight(.semibold)
                            }
                        }
                        .contentShape(Rectangle())
                        .onTapGesture { viewModel.selectAppMode(mode) }
                    }
                }
            }
            VFInfoRow(icon: "info.circle", text: "Seçilen alan, düzeltme kalitesini artırmak için bağlamı ayarlar.", color: .secondary)

            // Akıllı Düzeltme
            VFSectionHeader("Akıllı Düzeltme")
            VFCard {
                VFRow("Akıllı Düzeltme",
                      divider: viewModel.currentAppMode != .engineering) {
                    Toggle("", isOn: Binding(
                        get: { viewModel.isCorrectionEnabled },
                        set: { _ in viewModel.toggleCorrection() }
                    ))
                    .labelsHidden()
                    .disabled(viewModel.currentAppMode == .engineering)
                }
                if viewModel.currentAppMode != .engineering {
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
            if viewModel.currentAppMode == .engineering {
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
                            UserDefaults.standard.set(val, forKey: AppSettings.trainingMode)
                            viewModel.trainingModeEnabled = val
                        }
                }
            }
            VFInfoRow(icon: "info.circle", text: "Her transkripsiyondan sonra geri bildirim ekranı görünür. Düzeltmeleriniz doğruluğu artırır.", color: .secondary)
        }
        .padding(VFSpacing.xxxl)
    }
}

// MARK: - Knowledge Base

private struct KnowledgeBaseSection: View {
    var settingsVM: SettingsViewModel
    @State private var selectedFolderPath = ""

    var body: some View {
        VStack(alignment: .leading, spacing: VFSpacing.xxl) {

            VFSectionHeader("İndekslenen Projeler")
            VFCard {
                if settingsVM.indexedProjects.isEmpty {
                    HStack(spacing: VFSpacing.md) {
                        Image(systemName: VFIcon.circle).foregroundStyle(.secondary)
                        Text("Henüz eklenmedi").foregroundStyle(.secondary).font(VFFont.body)
                        Spacer()
                    }
                    .padding(.horizontal, VFSpacing.xxl)
                    .padding(.vertical, VFSpacing.xl)
                } else {
                    ForEach(Array(settingsVM.indexedProjects.enumerated()), id: \.element.id) { idx, project in
                        HStack(spacing: VFSpacing.md) {
                            Image(systemName: VFIcon.checkFill).foregroundStyle(VFColor.success)
                            VStack(alignment: .leading, spacing: VFSpacing.xxs) {
                                Text(project.name).font(VFFont.monospaced)
                                Text("\(project.symbolCount) sembol")
                                    .font(VFFont.caption).foregroundStyle(.secondary)
                            }
                            Spacer()
                        }
                        .padding(.horizontal, VFSpacing.xxl)
                        .padding(.vertical, VFSpacing.xl)
                        if idx < settingsVM.indexedProjects.count - 1 {
                            Divider().padding(.leading, VFSpacing.xxl)
                        }
                    }
                    Divider().padding(.leading, VFSpacing.xxl)
                    HStack {
                        Text("\(settingsVM.contextChunkCount) sözcük · \(settingsVM.indexedProjects.reduce(0) { $0 + $1.symbolCount }) sembol toplam")
                            .font(VFFont.caption).foregroundStyle(.secondary)
                        Spacer()
                        Button("Temizle") { settingsVM.clearContext() }
                            .buttonStyle(.plain).foregroundStyle(VFColor.destructive)
                            .font(VFFont.caption)
                    }
                    .padding(.horizontal, VFSpacing.xxl)
                    .padding(.vertical, VFSpacing.md)
                }
            }

            VFSectionHeader("Klasör Ekle")
            VFCard {
                VFRow("Klasör", divider: true) {
                    HStack(spacing: VFSpacing.md) {
                        TextField("Klasör yolu", text: $selectedFolderPath)
                            .textFieldStyle(.roundedBorder)
                            .font(VFFont.monospaced)
                        Button("Seç…") { pickFolder() }
                            .buttonStyle(.bordered)
                    }
                }
                HStack(spacing: VFSpacing.md) {
                    Button {
                        guard !selectedFolderPath.isEmpty else { return }
                        settingsVM.ingestContext(folderPath: selectedFolderPath)
                    } label: {
                        if settingsVM.isIndexing {
                            HStack(spacing: VFSpacing.sm) {
                                ProgressView().scaleEffect(0.7)
                                Text("İndeksleniyor…")
                            }
                        } else {
                            Text("Ekle")
                        }
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(selectedFolderPath.isEmpty || settingsVM.isIndexing)

                    if let error = settingsVM.contextIndexingError {
                        Text(error).font(VFFont.caption).foregroundStyle(VFColor.destructive)
                    }
                    Spacer()
                }
                .padding(.horizontal, VFSpacing.xxl)
                .padding(.vertical, VFSpacing.xl)
            }
            VFInfoRow(icon: "info.circle", text: "Kod tabanını tarar, class/method isimlerini otomatik sözlüğe ekler.", color: .secondary)
        }
        .padding(VFSpacing.xxxl)
        .onAppear { settingsVM.loadContextStatus() }
    }

    @MainActor
    private func pickFolder() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.allowsMultipleSelection = false
        panel.prompt = "Select Folder"
        if panel.runModal() == .OK, let url = panel.url {
            selectedFolderPath = url.path
        }
    }
}

// MARK: - Account

private struct AccountSection: View {
    var settingsVM: SettingsViewModel
    var viewModel: AppViewModel

    @State private var userName: String
    @State private var userDepartment: String

    init(settingsVM: SettingsViewModel, viewModel: AppViewModel) {
        self.settingsVM = settingsVM
        self.viewModel = viewModel
        _userName       = State(initialValue: settingsVM.userName)
        _userDepartment = State(initialValue: settingsVM.userDepartment)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: VFSpacing.xxl) {

            VFSectionHeader("Profil")
            VFCard {
                VFRow("Ad Soyad") {
                    TextField("Opsiyonel", text: $userName)
                        .textFieldStyle(.roundedBorder)
                        .frame(minWidth: VFLayout.fieldMedium)
                        .onChange(of: userName) { settingsVM.userName = userName }
                }
                VFRow("Departman") {
                    TextField("Opsiyonel", text: $userDepartment)
                        .textFieldStyle(.roundedBorder)
                        .frame(minWidth: VFLayout.fieldMedium)
                        .onChange(of: userDepartment) { settingsVM.userDepartment = userDepartment }
                }
                VFRow("Kullanıcı ID",
                      divider: viewModel.currentUser == nil) {
                    Text(settingsVM.userID.isEmpty ? "—" : settingsVM.userID)
                        .font(.system(.caption, design: .monospaced))
                        .foregroundStyle(.secondary)
                }
                if let user = viewModel.currentUser {
                    VFRow("Rol", divider: false) {
                        Text(user.role.capitalized)
                            .foregroundStyle(user.role == "admin" || user.role == "superadmin"
                                             ? VFColor.primary : .secondary)
                    }
                }
            }
        }
        .padding(VFSpacing.xxxl)
    }
}

// MARK: - About

private struct AboutSection: View {
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

