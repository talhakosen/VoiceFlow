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
        case .general:       return "gearshape"
        case .recording:     return "mic"
        case .dictionary:    return "character.book.closed"
        case .snippets:      return "text.badge.plus"
        case .knowledgeBase: return "books.vertical"
        case .account:       return "person.circle"
        case .about:         return "info.circle"
        }
    }
}

// MARK: - SettingsView (2-panel)

struct SettingsView: View {
    var viewModel: AppViewModel

    @State private var selectedSection: SettingsSection = .general
    @State private var columnVisibility: NavigationSplitViewVisibility = .all

    var body: some View {
        NavigationSplitView(columnVisibility: $columnVisibility) {
            List(SettingsSection.allCases, selection: $selectedSection) { section in
                Label(section.rawValue, systemImage: section.icon)
                    .tag(section)
                    .padding(.vertical, 3)
            }
            .listStyle(.sidebar)
            .navigationSplitViewColumnWidth(min: 190, ideal: 200)
            .toolbar(removing: .sidebarToggle)
            .safeAreaInset(edge: .top, spacing: 0) {
                HStack(spacing: 6) {
                    Image(systemName: "waveform")
                        .fontWeight(.semibold)
                    Text("VoiceFlow")
                        .fontWeight(.semibold)
                }
                .font(.title3)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
            }
        } detail: {
            ScrollView {
                Group {
                    switch selectedSection {
                    case .general:       GeneralSection()
                    case .recording:     RecordingSection(viewModel: viewModel)
                    case .dictionary:    DictionarySection(viewModel: viewModel)
                    case .snippets:      SnippetsSection(viewModel: viewModel)
                    case .knowledgeBase: KnowledgeBaseSection(viewModel: viewModel)
                    case .account:       AccountSection(viewModel: viewModel)
                    case .about:         AboutSection(viewModel: viewModel)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .topLeading)
            }
        }
        .navigationSplitViewStyle(.balanced)
        .toolbar {
            ToolbarItem(placement: .navigation) {
                Button {
                    withAnimation {
                        columnVisibility = columnVisibility == .detailOnly ? .all : .detailOnly
                    }
                } label: {
                    Image(systemName: "sidebar.left")
                }
            }
        }
        .frame(width: 900, height: 620)
    }
}

// MARK: - General

private struct GeneralSection: View {
    @AppStorage(AppSettings.deploymentMode) private var deploymentMode = "local"
    @AppStorage(AppSettings.serverURL)      private var serverURL      = "http://127.0.0.1:8765"
    @AppStorage(AppSettings.apiKey)         private var apiKey         = ""
    @State private var showRestartNotice = false

    var body: some View {
        Form {
            Section("Kısayol") {
                LabeledContent("Tuş") {
                    Text("Fn × 2  (kayıt başlat/durdur)")
                        .foregroundStyle(.secondary)
                }
                LabeledContent("Zorla Durdur") {
                    Text("⌘S  menü çubuğundan")
                        .foregroundStyle(.secondary)
                }
            }

            Section("Bağlantı") {
                Picker("Dağıtım Modu", selection: $deploymentMode) {
                    Text("Yerel (Mac — MLX)").tag("local")
                    Text("Sunucu (Şirket İçi)").tag("server")
                }
                .onChange(of: deploymentMode) { showRestartNotice = true }

                if deploymentMode == "server" {
                    LabeledContent("Sunucu Adresi") {
                        TextField("https://voiceflow.company.internal:8765", text: $serverURL)
                            .textFieldStyle(.roundedBorder)
                            .frame(minWidth: 360)
                    }
                    LabeledContent("API Anahtarı") {
                        SecureField("API anahtarını yapıştırın", text: $apiKey)
                            .textFieldStyle(.roundedBorder)
                            .frame(minWidth: 360)
                    }
                    HStack(spacing: 6) {
                        Image(systemName: "lock.shield").foregroundStyle(.green)
                        Text("All audio processing happens on your server. No data leaves your network.")
                            .font(.caption).foregroundStyle(.secondary)
                    }
                }
            }

            if showRestartNotice {
                Section {
                    HStack(spacing: 6) {
                        Image(systemName: "arrow.clockwise.circle").foregroundStyle(.orange)
                        Text("Modu değiştirmek için VoiceFlow'u yeniden başlatın.")
                            .font(.caption).foregroundStyle(.secondary)
                    }
                }
            }
        }
        .formStyle(.grouped)
        .padding()
    }
}

// MARK: - Dictionary

private struct DictionarySection: View {
    var viewModel: AppViewModel

    @State private var selectedTab = 0
    @State private var newTrigger = ""
    @State private var newReplacement = ""

    private var personalEntries: [DictionaryEntry] {
        viewModel.dictionaryEntries.filter { $0.scope == "personal" }
    }

    private var teamEntries: [DictionaryEntry] {
        viewModel.dictionaryEntries.filter { $0.scope == "team" }
    }

    // Check if a personal entry already exists in team
    private func isSharedWithTeam(_ entry: DictionaryEntry) -> Bool {
        teamEntries.contains { $0.trigger == entry.trigger && $0.replacement == entry.replacement }
    }

    var body: some View {
        VStack(spacing: 0) {
            // Tab picker
            Picker("", selection: $selectedTab) {
                Text("Kişisel (\(personalEntries.count))").tag(0)
                Text("Takım (\(teamEntries.count))").tag(1)
            }
            .pickerStyle(.segmented)
            .padding(.horizontal)
            .padding(.top, 12)
            .padding(.bottom, 8)

            Form {
                Section {
                    if selectedTab == 0 {
                        if personalEntries.isEmpty {
                            Text("Henüz kişisel kural yok. Ses düzeltmelerin otomatik buraya eklenir.")
                                .foregroundStyle(.secondary)
                                .font(.callout)
                        } else {
                            ForEach(personalEntries) { entry in
                                DictionaryRow(
                                    entry: entry,
                                    alreadyShared: isSharedWithTeam(entry),
                                    onDelete: { viewModel.deleteDictionaryEntry(id: entry.id) },
                                    onShareToTeam: {
                                        viewModel.addDictionaryEntry(
                                            trigger: entry.trigger,
                                            replacement: entry.replacement,
                                            scope: "team"
                                        )
                                    }
                                )
                            }
                        }
                    } else {
                        if teamEntries.isEmpty {
                            Text("Takım kuralı yok. Kişisel kurallarını takıma ekleyebilirsin.")
                                .foregroundStyle(.secondary)
                                .font(.callout)
                        } else {
                            ForEach(teamEntries) { entry in
                                DictionaryRow(
                                    entry: entry,
                                    alreadyShared: false,
                                    onDelete: { viewModel.deleteDictionaryEntry(id: entry.id) },
                                    onShareToTeam: nil
                                )
                            }
                        }
                    }
                } header: {
                    Text(selectedTab == 0 ? "Kişisel Kurallar" : "Takım Kuralları")
                }

                Section {
                    HStack(spacing: 8) {
                        TextField("kelime (örn: voisflow)", text: $newTrigger)
                            .textFieldStyle(.roundedBorder)
                        Image(systemName: "arrow.right").foregroundStyle(.secondary)
                        TextField("doğru yazım (örn: VoiceFlow)", text: $newReplacement)
                            .textFieldStyle(.roundedBorder)
                        Button("Ekle") {
                            guard !newTrigger.isEmpty, !newReplacement.isEmpty else { return }
                            let scope = selectedTab == 0 ? "personal" : "team"
                            viewModel.addDictionaryEntry(trigger: newTrigger, replacement: newReplacement, scope: scope)
                            newTrigger = ""
                            newReplacement = ""
                        }
                        .buttonStyle(.borderedProminent)
                        .disabled(newTrigger.isEmpty || newReplacement.isEmpty)
                    }
                    Text("Whisper sonrası, düzeltme öncesi uygulanır. Büyük/küçük harf duyarsız, kelime sınırı korunur.")
                        .font(.caption).foregroundStyle(.secondary)
                } header: {
                    Text(selectedTab == 0 ? "Kişisel Kural Ekle" : "Takım Kuralı Ekle")
                }
            }
            .formStyle(.grouped)
        }
        .onAppear { viewModel.loadDictionary() }
    }
}

private struct DictionaryRow: View {
    let entry: DictionaryEntry
    let alreadyShared: Bool
    let onDelete: () -> Void
    let onShareToTeam: (() -> Void)?

    var body: some View {
        HStack {
            Text(entry.trigger)
                .frame(minWidth: 100, alignment: .leading)
                .foregroundStyle(.primary)
            Image(systemName: "arrow.right")
                .foregroundStyle(.secondary)
                .font(.caption)
            Text(entry.replacement)
                .frame(maxWidth: .infinity, alignment: .leading)
                .foregroundStyle(.primary)

            if let share = onShareToTeam {
                Button {
                    share()
                } label: {
                    Label(alreadyShared ? "Eklendi" : "Takıma ekle", systemImage: alreadyShared ? "checkmark" : "person.2.badge.plus")
                        .font(.caption)
                        .foregroundStyle(alreadyShared ? Color.secondary : Color.blue)
                }
                .buttonStyle(.plain)
                .disabled(alreadyShared)
            }

            Button {
                onDelete()
            } label: {
                Image(systemName: "trash")
                    .foregroundStyle(.red)
            }
            .buttonStyle(.plain)
        }
    }
}

// MARK: - Snippets

private struct SnippetsSection: View {
    var viewModel: AppViewModel

    @State private var newTrigger = ""
    @State private var newExpansion = ""
    @State private var newScope = "personal"

    var body: some View {
        Form {
            Section {
                if viewModel.snippetEntries.isEmpty {
                    Text("Henüz şablon yok. Ses kaydında tetikleyici söyleyince şablon yapıştırılır.")
                        .foregroundStyle(.secondary)
                } else {
                    ForEach(viewModel.snippetEntries) { entry in
                        HStack {
                            Text(entry.triggerPhrase)
                                .frame(minWidth: 100, alignment: .leading)
                            Image(systemName: "arrow.right")
                                .foregroundStyle(.secondary)
                            Text(entry.expansion)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .lineLimit(2)
                            Text(entry.scope == "personal" ? "Kişisel" : "Takım")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                                .frame(width: 60)
                            if entry.scope == "personal" {
                                Button {
                                    viewModel.deleteSnippet(id: entry.id)
                                } label: {
                                    Image(systemName: "trash")
                                        .foregroundStyle(.red)
                                }
                                .buttonStyle(.plain)
                            }
                        }
                    }
                }
            } header: {
                Text("Şablon Listesi")
            }

            Section("Şablon Ekle") {
                HStack(spacing: 8) {
                    TextField("tetikleyici (örn: standart imza)", text: $newTrigger)
                        .textFieldStyle(.roundedBorder)
                    Image(systemName: "arrow.right").foregroundStyle(.secondary)
                    TextField("içerik (açılacak metin)", text: $newExpansion)
                        .textFieldStyle(.roundedBorder)
                    Picker("", selection: $newScope) {
                        Text("Kişisel").tag("personal")
                        Text("Takım").tag("team")
                    }
                    .frame(width: 90)
                    Button("Ekle") {
                        guard !newTrigger.isEmpty, !newExpansion.isEmpty else { return }
                        viewModel.addSnippet(triggerPhrase: newTrigger, expansion: newExpansion, scope: newScope)
                        newTrigger = ""
                        newExpansion = ""
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(newTrigger.isEmpty || newExpansion.isEmpty)
                }

                Text("Tetikleyici kelime sesi tam eşleştiğinde şablon metnini yapıştırır. Sözlükten sonra, düzeltmeden önce uygulanır.")
                    .font(.caption).foregroundStyle(.secondary)
            }
        }
        .formStyle(.grouped)
        .padding()
        .onAppear { viewModel.loadSnippets() }
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
        Form {
            Section("Dil") {
                Picker("Dil", selection: Binding(
                    get: { viewModel.currentLanguageMode },
                    set: { viewModel.selectLanguageMode($0) }
                )) {
                    ForEach(LanguageMode.allCases, id: \.self) { mode in
                        Text(mode.rawValue).tag(mode)
                    }
                }
            }

            Section("Bağlam") {
                Picker("Kullanım Alanı", selection: Binding(
                    get: { viewModel.currentAppMode },
                    set: { viewModel.selectAppMode($0) }
                )) {
                    ForEach(AppMode.allCases, id: \.self) { mode in
                        Text(mode.displayName).tag(mode)
                    }
                }
                .pickerStyle(.radioGroup)

                Text("Seçilen alan, düzeltme kalitesini artırmak için bağlamı ayarlar.")
                    .font(.caption).foregroundStyle(.secondary)
            }

            Section("Akıllı Düzeltme") {
                Toggle("Akıllı Düzeltme", isOn: Binding(
                    get: { viewModel.isCorrectionEnabled },
                    set: { _ in viewModel.toggleCorrection() }
                ))

                Picker("Yapay Zeka Motoru", selection: $llmMode) {
                    Text("Yerel (Mac — MLX Qwen 7B)").tag("local")
                    Text("Bulut (RunPod — Ollama Qwen 7B)").tag("cloud")
                    Text("Alibaba (Qwen Max — API)").tag("alibaba")
                }
                .onChange(of: llmMode) { showRestartNotice = true }

                if llmMode == "cloud" {
                    LabeledContent("Ollama URL") {
                        TextField("https://…-11434.proxy.runpod.net", text: $llmEndpoint)
                            .textFieldStyle(.roundedBorder)
                            .frame(minWidth: 360)
                            .onChange(of: llmEndpoint) { showRestartNotice = true }
                    }
                }

                if llmMode == "alibaba" {
                    HStack(spacing: 6) {
                        Image(systemName: "bolt.fill").foregroundStyle(.orange)
                        Text("Alibaba DashScope — qwen-max. Hızlı, yüksek kalite. İnternet gerektirir.")
                            .font(.caption).foregroundStyle(.secondary)
                    }
                }

                if showRestartNotice {
                    HStack(spacing: 6) {
                        Image(systemName: "arrow.clockwise.circle").foregroundStyle(.orange)
                        Text("Değişikliği uygulamak için servisi yeniden başlatın.")
                            .font(.caption).foregroundStyle(.secondary)
                    }
                }
            }

            Section("Kişisel Ses Tanıma") {
                Toggle("Kişisel Ses Tanıma", isOn: $trainingMode)
                    .onChange(of: trainingMode) { _, val in
                        UserDefaults.standard.set(val, forKey: AppSettings.trainingMode)
                        viewModel.trainingModeEnabled = val
                    }

                Text("Her transkripsiyondan sonra geri bildirim ekranı görünür. Düzeltmeleriniz doğruluğu artırır.")
                    .font(.caption).foregroundStyle(.secondary)
            }
        }
        .formStyle(.grouped)
        .padding()
    }
}

// MARK: - Knowledge Base

private struct KnowledgeBaseSection: View {
    var viewModel: AppViewModel
    @State private var selectedFolderPath = ""

    var body: some View {
        Form {
            Section("Durum") {
                HStack {
                    Image(systemName: viewModel.contextChunkCount > 0 ? "checkmark.circle.fill" : "circle")
                        .foregroundStyle(viewModel.contextChunkCount > 0 ? .green : .secondary)
                    if viewModel.contextChunkCount > 0 {
                        Text("\(viewModel.contextChunkCount) bölüm eklendi")
                    } else {
                        Text("Henüz eklenmedi").foregroundStyle(.secondary)
                    }
                    Spacer()
                    if viewModel.contextChunkCount > 0 {
                        Button("Temizle") { viewModel.clearContext() }
                            .buttonStyle(.plain).foregroundStyle(.red)
                    }
                }
            }

            Section("Klasör Ekle") {
                HStack {
                    TextField("Klasör yolu", text: $selectedFolderPath)
                        .textFieldStyle(.roundedBorder)
                        .font(.system(.body, design: .monospaced))
                    Button("Seç…") { pickFolder() }
                }

                Text("Supported: .txt .md .py .swift .ts .js .go .java .yaml .json")
                    .font(.caption).foregroundStyle(.secondary)

                Button {
                    guard !selectedFolderPath.isEmpty else { return }
                    viewModel.ingestContext(folderPath: selectedFolderPath)
                } label: {
                    if viewModel.isIndexing {
                        HStack(spacing: 6) {
                            ProgressView().scaleEffect(0.7)
                            Text("Indexing…")
                        }
                    } else {
                        Text("Ekle")
                    }
                }
                .buttonStyle(.borderedProminent)
                .disabled(selectedFolderPath.isEmpty || viewModel.isIndexing)

                if let error = viewModel.contextIndexingError {
                    Text(error).font(.caption).foregroundStyle(.red)
                }
            }
        }
        .formStyle(.grouped)
        .padding()
        .onAppear { viewModel.loadContextStatus() }
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
    var viewModel: AppViewModel

    @State private var userName: String
    @State private var userDepartment: String

    init(viewModel: AppViewModel) {
        self.viewModel = viewModel
        _userName       = State(initialValue: viewModel.userName)
        _userDepartment = State(initialValue: viewModel.userDepartment)
    }

    var body: some View {
        Form {
            Section("Profile") {
                LabeledContent("Ad Soyad") {
                    TextField("Opsiyonel", text: $userName)
                        .textFieldStyle(.roundedBorder)
                        .frame(minWidth: 320)
                        .onChange(of: userName) { viewModel.userName = userName }
                }
                LabeledContent("Departman") {
                    TextField("Opsiyonel", text: $userDepartment)
                        .textFieldStyle(.roundedBorder)
                        .frame(minWidth: 320)
                        .onChange(of: userDepartment) { viewModel.userDepartment = userDepartment }
                }
                LabeledContent("Kullanıcı ID") {
                    Text(viewModel.userID.isEmpty ? "—" : viewModel.userID)
                        .font(.caption.monospaced())
                        .foregroundStyle(.secondary)
                }
                if let user = viewModel.currentUser {
                    LabeledContent("Rol") {
                        Text(user.role.capitalized)
                            .foregroundStyle(user.role == "admin" || user.role == "superadmin" ? .blue : .secondary)
                    }
                }
            }
        }
        .formStyle(.grouped)
        .padding()
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
        Form {
            Section("VoiceFlow") {
                LabeledContent("Sürüm") {
                    Text("v\(appVersion)").foregroundStyle(.secondary)
                }
                LabeledContent("Durum") {
                    Text(viewModel.statusText).foregroundStyle(.secondary)
                }
            }

            Section("Servis Yönetimi") {
                Button("Servisi Yeniden Başlat") { viewModel.restartBackend() }
                    .buttonStyle(.bordered)

                Button("Sıfırla") { viewModel.hardReset() }
                    .buttonStyle(.bordered)
                    .foregroundStyle(.red)

                Text("Sıfırlama, arka plan servisini tamamen durdurur ve yeniden başlatır.")
                    .font(.caption).foregroundStyle(.secondary)
            }
        }
        .formStyle(.grouped)
        .padding()
    }
}
