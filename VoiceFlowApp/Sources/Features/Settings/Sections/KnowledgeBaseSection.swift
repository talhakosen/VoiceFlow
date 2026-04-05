import ComposableArchitecture
import SwiftUI
import AppKit

// MARK: - Knowledge Base

struct KnowledgeBaseSection: View {
    let store: StoreOf<SettingsFeature>
    @State private var selectedFolderPath = ""

    var body: some View {
        let state = store.state
        VStack(alignment: .leading, spacing: VFSpacing.xxl) {

            VFSectionHeader("İndekslenen Projeler")
            VFCard {
                if state.indexedProjects.isEmpty {
                    HStack(spacing: VFSpacing.md) {
                        Image(systemName: VFIcon.circle).foregroundStyle(.secondary)
                        Text("Henüz eklenmedi").foregroundStyle(.secondary).font(VFFont.body)
                        Spacer()
                    }
                    .padding(.horizontal, VFSpacing.xxl)
                    .padding(.vertical, VFSpacing.xl)
                } else {
                    ForEach(Array(state.indexedProjects.enumerated()), id: \.element.id) { idx, project in
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
                        if idx < state.indexedProjects.count - 1 {
                            Divider().padding(.leading, VFSpacing.xxl)
                        }
                    }
                    Divider().padding(.leading, VFSpacing.xxl)
                    HStack {
                        Text("\(state.contextChunkCount) sözcük · \(state.indexedProjects.reduce(0) { $0 + $1.symbolCount }) sembol toplam")
                            .font(VFFont.caption).foregroundStyle(.secondary)
                        Spacer()
                        Button("Temizle") { store.send(.clearContext) }
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
                        store.send(.ingestContext(folderPath: selectedFolderPath))
                    } label: {
                        if state.isIndexing {
                            HStack(spacing: VFSpacing.sm) {
                                ProgressView().scaleEffect(0.7)
                                Text("İndeksleniyor…")
                            }
                        } else {
                            Text("Ekle")
                        }
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(selectedFolderPath.isEmpty || state.isIndexing)

                    if let error = state.contextIndexingError {
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
        .onAppear { store.send(.loadContextStatus) }
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
