import SwiftUI

// MARK: - UserDefaults Keys

enum AppSettings {
    static let deploymentMode      = "deploymentMode"       // "local" | "server"
    static let serverURL           = "serverURL"
    static let apiKey              = "apiKey"
    static let appMode             = "appMode"              // "general" | "engineering" | "office"
    static let onboardingComplete  = "onboardingComplete"   // Bool
    static let defaultLanguage     = "defaultLanguage"      // "tr" | "en" | "auto"
    static let userID              = "userID"               // UUID string, auto-generated
    static let userName            = "userName"             // display name (optional)
    static let userDepartment      = "userDepartment"       // department (optional)
}

// MARK: - SettingsView

struct SettingsView: View {
    @AppStorage(AppSettings.deploymentMode) private var deploymentMode = "local"
    @AppStorage(AppSettings.serverURL)      private var serverURL      = "http://127.0.0.1:8765"
    @AppStorage(AppSettings.apiKey)         private var apiKey         = ""
    @AppStorage(AppSettings.userName)       private var userName       = ""
    @AppStorage(AppSettings.userDepartment) private var userDepartment = ""
    @AppStorage(AppSettings.userID)         private var userID         = ""

    var viewModel: AppViewModel? = nil

    @State private var showRestartNotice = false
    @State private var showContextSheet = false

    var body: some View {
        Form {
            Section {
                Picker("Deployment Mode", selection: $deploymentMode) {
                    Text("Local (Mac)").tag("local")
                    Text("Server (On-Premise / RunPod)").tag("server")
                }
                .pickerStyle(.segmented)
                .onChange(of: deploymentMode) {
                    showRestartNotice = true
                }
            } header: {
                Text("Connection")
                    .font(.headline)
            }

            if deploymentMode == "server" {
                Section {
                    LabeledContent("Server URL") {
                        TextField("https://voiceflow.company.internal:8765", text: $serverURL)
                            .textFieldStyle(.roundedBorder)
                            .frame(minWidth: 280)
                    }

                    LabeledContent("API Key") {
                        SecureField("Paste API key here", text: $apiKey)
                            .textFieldStyle(.roundedBorder)
                            .frame(minWidth: 280)
                    }
                } header: {
                    Text("Server Configuration")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }

                Section {
                    HStack(spacing: 6) {
                        Image(systemName: "lock.shield")
                            .foregroundStyle(.green)
                        Text("All audio processing happens on your server. No data leaves your network.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }

            Section {
                LabeledContent("Ad Soyad") {
                    TextField("Opsiyonel", text: $userName)
                        .textFieldStyle(.roundedBorder)
                        .frame(minWidth: 200)
                }
                LabeledContent("Departman") {
                    TextField("Opsiyonel", text: $userDepartment)
                        .textFieldStyle(.roundedBorder)
                        .frame(minWidth: 200)
                }
                LabeledContent("Kullanıcı ID") {
                    Text(userID.isEmpty ? "—" : userID)
                        .font(.caption.monospaced())
                        .foregroundStyle(.secondary)
                }
            } header: {
                Text("Profil")
                    .font(.headline)
            }

            if showRestartNotice {
                Section {
                    HStack(spacing: 6) {
                        Image(systemName: "arrow.clockwise.circle")
                            .foregroundStyle(.orange)
                        Text("Restart VoiceFlow to apply mode change.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }

            if let vm = viewModel {
                Section {
                    HStack {
                        VStack(alignment: .leading, spacing: 2) {
                            Text("Knowledge Base")
                            Text(vm.contextChunkCount > 0
                                 ? "\(vm.contextChunkCount) chunks indexed"
                                 : "Not indexed")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        Spacer()
                        Button("Manage…") {
                            showContextSheet = true
                        }
                    }
                } header: {
                    Text("Context Engine")
                        .font(.headline)
                }
            }
        }
        .formStyle(.grouped)
        .padding()
        .frame(width: 460)
        .sheet(isPresented: $showContextSheet) {
            if let vm = viewModel {
                ContextView(viewModel: vm)
            }
        }
    }
}
