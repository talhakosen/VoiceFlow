import SwiftUI
import AppKit

// MARK: - Knowledge Base

struct KnowledgeBaseSection: View {
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
