import SwiftUI
import AppKit

/// Knowledge base management — folder selection, indexing, status.
/// Presented as a sheet from SettingsView.
struct ContextView: View {
    @Environment(\.dismiss) private var dismiss

    var settingsVM: SettingsViewModel

    @State private var selectedFolderPath: String = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            Text("Knowledge Base")
                .font(.headline)

            // Status
            GroupBox("Index Status") {
                HStack {
                    Image(systemName: settingsVM.contextChunkCount > 0 ? "checkmark.circle.fill" : "circle")
                        .foregroundColor(settingsVM.contextChunkCount > 0 ? .green : .secondary)
                    if settingsVM.contextChunkCount > 0 {
                        Text("\(settingsVM.contextChunkCount) chunks indexed")
                    } else {
                        Text("Not indexed")
                            .foregroundColor(.secondary)
                    }
                    Spacer()
                    if settingsVM.contextChunkCount > 0 {
                        Button("Clear") {
                            settingsVM.clearContext()
                        }
                        .buttonStyle(.plain)
                        .foregroundColor(.red)
                    }
                }
                .padding(.vertical, 4)
            }

            // Folder selection
            GroupBox("Index a Folder") {
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        TextField("Folder path", text: $selectedFolderPath)
                            .textFieldStyle(.roundedBorder)
                            .font(.system(.body, design: .monospaced))

                        Button("Browse…") {
                            pickFolder()
                        }
                    }

                    Text("Supported: .txt .md .py .swift .ts .js .go .java .yaml .json")
                        .font(.caption)
                        .foregroundColor(.secondary)

                    HStack {
                        Button(action: {
                            guard !selectedFolderPath.isEmpty else { return }
                            settingsVM.ingestContext(folderPath: selectedFolderPath)
                        }) {
                            if settingsVM.isIndexing {
                                ProgressView()
                                    .scaleEffect(0.7)
                                    .padding(.trailing, 4)
                                Text("Indexing…")
                            } else {
                                Text("Index Now")
                            }
                        }
                        .disabled(selectedFolderPath.isEmpty || settingsVM.isIndexing)
                        .buttonStyle(.borderedProminent)

                        Spacer()
                    }

                    if let error = settingsVM.contextIndexingError {
                        Text(error)
                            .font(.caption)
                            .foregroundColor(.red)
                    }
                }
                .padding(.vertical, 4)
            }

            Spacer()

            HStack {
                Spacer()
                Button("Done") { dismiss() }
                    .keyboardShortcut(.defaultAction)
            }
        }
        .padding(20)
        .frame(width: 460, height: 300)
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
