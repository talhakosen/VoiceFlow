import ComposableArchitecture
import SwiftUI
import AppKit

// MARK: - Knowledge Base

struct KnowledgeBaseSection: View {
    let store: StoreOf<SettingsFeature>
    @State private var selectedFolderPath = ""

    var body: some View {
        let state = store.state
        VStack(alignment: .leading, spacing: 28) {

            Text("Bilgi Tabanı")
                .font(.system(size: 22, weight: .bold))
                .padding(.bottom, 4)

            // İndekslenen projeler
            SettingsCardSection(title: "İndekslenen Projeler") {
                if state.indexedProjects.isEmpty {
                    HStack(spacing: 10) {
                        Image(systemName: VFIcon.circle).foregroundStyle(.tertiary)
                        Text("Henüz proje eklenmedi").foregroundStyle(.secondary).font(.system(size: 13))
                        Spacer()
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 14)
                } else {
                    ForEach(Array(state.indexedProjects.enumerated()), id: \.element.id) { idx, project in
                        let isLast = idx == state.indexedProjects.count - 1
                        VStack(spacing: 0) {
                            HStack(spacing: 10) {
                                Image(systemName: VFIcon.checkFill).foregroundStyle(VFColor.success)
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(project.name).font(.system(size: 13, weight: .medium, design: .monospaced))
                                    Text("\(project.symbolCount) sembol")
                                        .font(.caption).foregroundStyle(.secondary)
                                }
                                Spacer()
                            }
                            .padding(.horizontal, 16)
                            .padding(.vertical, 11)
                            if !isLast { Divider().padding(.leading, 16) }
                        }
                    }
                    Divider().padding(.leading, 16)
                    HStack {
                        Text("\(state.contextChunkCount) sözcük · \(state.indexedProjects.reduce(0) { $0 + $1.symbolCount }) sembol toplam")
                            .font(.caption).foregroundStyle(.secondary)
                        Spacer()
                        Button("Temizle") { store.send(.clearContext) }
                            .buttonStyle(.plain).foregroundStyle(VFColor.destructive).font(.caption)
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 10)
                }
            }

            // Klasör ekle
            SettingsCardSection(title: "Klasör Ekle") {
                SettingsRow(title: "Klasör Yolu", subtitle: "Kod tabanı klasörünü seçin; class/method isimleri sözlüğe eklenir", isLast: false) {
                    HStack(spacing: 8) {
                        TextField("Klasör yolu", text: $selectedFolderPath)
                            .textFieldStyle(.roundedBorder)
                            .font(.system(.body, design: .monospaced))
                        Button("Seç…") { pickFolder() }.buttonStyle(.bordered)
                    }
                }
                HStack(spacing: 12) {
                    Button {
                        guard !selectedFolderPath.isEmpty else { return }
                        store.send(.ingestContext(folderPath: selectedFolderPath))
                    } label: {
                        if state.isIndexing {
                            HStack(spacing: 6) {
                                ProgressView().scaleEffect(0.7)
                                Text("İndeksleniyor…")
                            }
                        } else {
                            Text("Ekle ve İndeksle")
                        }
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(selectedFolderPath.isEmpty || state.isIndexing)

                    if let error = state.contextIndexingError {
                        Text(error).font(.caption).foregroundStyle(VFColor.destructive)
                    }
                    Spacer()
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 14)
            }

            InfoNote(icon: "info.circle", text: "Kod tabanı taranır; class/struct/func isimleri otomatik sözlüğe eklenir. Mühendislik modunda @sembol enjeksiyonu aktiftir.", color: .secondary)

            Spacer()
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
        panel.prompt = "Klasör Seç"
        if panel.runModal() == .OK, let url = panel.url {
            selectedFolderPath = url.path
        }
    }
}
