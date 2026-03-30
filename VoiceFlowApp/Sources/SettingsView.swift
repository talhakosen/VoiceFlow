import SwiftUI
import AppKit

// MARK: - Settings Section

private enum SettingsSection: String, CaseIterable, Identifiable {
    case general       = "General"
    case recording     = "Recording"
    case dictionary    = "Dictionary"
    case knowledgeBase = "Knowledge Base"
    case account       = "Account"
    case about         = "About"

    var id: String { rawValue }

    var icon: String {
        switch self {
        case .general:       return "gearshape"
        case .recording:     return "mic"
        case .dictionary:    return "character.book.closed"
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
        } detail: {
            ScrollView {
                Group {
                    switch selectedSection {
                    case .general:       GeneralSection()
                    case .recording:     RecordingSection(viewModel: viewModel)
                    case .dictionary:    DictionarySection(viewModel: viewModel)
                    case .knowledgeBase: KnowledgeBaseSection(viewModel: viewModel)
                    case .account:       AccountSection(viewModel: viewModel)
                    case .about:         AboutSection(viewModel: viewModel)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .topLeading)
            }
            .toolbar {
                ToolbarItem(placement: .navigation) {
                    Button {
                        withAnimation {
                            columnVisibility = columnVisibility == .detailOnly ? .all : .detailOnly
                        }
                    } label: {
                        Image(systemName: "sidebar.left")
                    }
                    .help("Toggle Sidebar")
                }
            }
        }
        .navigationSplitViewStyle(.balanced)
        .toolbar(removing: .sidebarToggle)
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
            Section("Shortcut") {
                LabeledContent("Hotkey") {
                    Text("Fn × 2  (double-tap to toggle recording)")
                        .foregroundStyle(.secondary)
                }
                LabeledContent("Force Stop") {
                    Text("⌘S  from menu bar")
                        .foregroundStyle(.secondary)
                }
            }

            Section("Connection") {
                Picker("Deployment Mode", selection: $deploymentMode) {
                    Text("Local (Mac — MLX)").tag("local")
                    Text("Server (On-Premise / RunPod)").tag("server")
                }
                .onChange(of: deploymentMode) { showRestartNotice = true }

                if deploymentMode == "server" {
                    LabeledContent("Server URL") {
                        TextField("https://voiceflow.company.internal:8765", text: $serverURL)
                            .textFieldStyle(.roundedBorder)
                            .frame(minWidth: 360)
                    }
                    LabeledContent("API Key") {
                        SecureField("Paste API key here", text: $apiKey)
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
                        Text("Restart VoiceFlow to apply mode change.")
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

    @State private var newTrigger = ""
    @State private var newReplacement = ""
    @State private var newScope = "personal"

    var body: some View {
        Form {
            Section {
                if viewModel.dictionaryEntries.isEmpty {
                    Text("No entries yet.").foregroundStyle(.secondary)
                } else {
                    ForEach(viewModel.dictionaryEntries) { entry in
                        HStack {
                            Text(entry.trigger)
                                .frame(minWidth: 80, alignment: .leading)
                            Image(systemName: "arrow.right")
                                .foregroundStyle(.secondary)
                            Text(entry.replacement)
                                .frame(maxWidth: .infinity, alignment: .leading)
                            Text(entry.scope)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                                .frame(width: 60)
                            if entry.scope == "personal" {
                                Button {
                                    viewModel.deleteDictionaryEntry(id: entry.id)
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
                Text("Entries")
            }

            Section("Add Entry") {
                HStack(spacing: 8) {
                    TextField("trigger (e.g. btw)", text: $newTrigger)
                        .textFieldStyle(.roundedBorder)
                    Image(systemName: "arrow.right").foregroundStyle(.secondary)
                    TextField("replacement", text: $newReplacement)
                        .textFieldStyle(.roundedBorder)
                    Picker("", selection: $newScope) {
                        Text("Personal").tag("personal")
                        Text("Team").tag("team")
                    }
                    .frame(width: 90)
                    Button("Add") {
                        guard !newTrigger.isEmpty, !newReplacement.isEmpty else { return }
                        viewModel.addDictionaryEntry(trigger: newTrigger, replacement: newReplacement, scope: newScope)
                        newTrigger = ""
                        newReplacement = ""
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(newTrigger.isEmpty || newReplacement.isEmpty)
                }

                Text("Applied after Whisper, before LLM correction. Word-boundary match, case-insensitive.")
                    .font(.caption).foregroundStyle(.secondary)
            }
        }
        .formStyle(.grouped)
        .padding()
        .onAppear { viewModel.loadDictionary() }
    }
}

// MARK: - Recording

private struct RecordingSection: View {
    var viewModel: AppViewModel

    var body: some View {
        Form {
            Section("Language") {
                Picker("Language", selection: Binding(
                    get: { viewModel.currentLanguageMode },
                    set: { viewModel.selectLanguageMode($0) }
                )) {
                    ForEach(LanguageMode.allCases, id: \.self) { mode in
                        Text(mode.rawValue).tag(mode)
                    }
                }
            }

            Section("Mode") {
                Picker("Transcription Mode", selection: Binding(
                    get: { viewModel.currentAppMode },
                    set: { viewModel.selectAppMode($0) }
                )) {
                    ForEach(AppMode.allCases, id: \.self) { mode in
                        Text(mode.displayName).tag(mode)
                    }
                }
                .pickerStyle(.radioGroup)

                Text("Mode adjusts the LLM system prompt for better context-specific corrections.")
                    .font(.caption).foregroundStyle(.secondary)
            }

            Section("LLM Correction") {
                Toggle("Smart Correction (Qwen 7B)", isOn: Binding(
                    get: { viewModel.isCorrectionEnabled },
                    set: { _ in viewModel.toggleCorrection() }
                ))
                Text("Loads a ~4 GB model on first use. Corrects punctuation, capitalisation, and Turkish characters.")
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
            Section("Index Status") {
                HStack {
                    Image(systemName: viewModel.contextChunkCount > 0 ? "checkmark.circle.fill" : "circle")
                        .foregroundStyle(viewModel.contextChunkCount > 0 ? .green : .secondary)
                    if viewModel.contextChunkCount > 0 {
                        Text("\(viewModel.contextChunkCount) chunks indexed")
                    } else {
                        Text("Not indexed").foregroundStyle(.secondary)
                    }
                    Spacer()
                    if viewModel.contextChunkCount > 0 {
                        Button("Clear") { viewModel.clearContext() }
                            .buttonStyle(.plain).foregroundStyle(.red)
                    }
                }
            }

            Section("Index a Folder") {
                HStack {
                    TextField("Folder path", text: $selectedFolderPath)
                        .textFieldStyle(.roundedBorder)
                        .font(.system(.body, design: .monospaced))
                    Button("Browse…") { pickFolder() }
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
                        Text("Index Now")
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
        Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "0.2"
    }

    var body: some View {
        Form {
            Section("VoiceFlow") {
                LabeledContent("Version") {
                    Text("v\(appVersion)").foregroundStyle(.secondary)
                }
                LabeledContent("Backend") {
                    Text(viewModel.statusText).foregroundStyle(.secondary)
                }
            }

            Section("Backend Control") {
                Button("Restart Backend") { viewModel.restartBackend() }
                    .buttonStyle(.bordered)

                Button("Hard Reset Backend") { viewModel.hardReset() }
                    .buttonStyle(.bordered)
                    .foregroundStyle(.red)

                Text("Hard reset kills the backend process and restarts from scratch.")
                    .font(.caption).foregroundStyle(.secondary)
            }
        }
        .formStyle(.grouped)
        .padding()
    }
}
