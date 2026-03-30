import SwiftUI

// MARK: - UserDefaults Keys

enum AppSettings {
    static let deploymentMode = "deploymentMode"  // "local" | "server"
    static let serverURL      = "serverURL"
    static let apiKey         = "apiKey"
}

// MARK: - SettingsView

struct SettingsView: View {
    @AppStorage(AppSettings.deploymentMode) private var deploymentMode = "local"
    @AppStorage(AppSettings.serverURL)      private var serverURL      = "http://127.0.0.1:8765"
    @AppStorage(AppSettings.apiKey)         private var apiKey         = ""

    @State private var showRestartNotice = false

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
        }
        .formStyle(.grouped)
        .padding()
        .frame(width: 460)
    }
}
