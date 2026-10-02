import ComposableArchitecture
import SwiftUI
import AppKit

// MARK: - Project Terms (smart dictionary from a code folder)

struct KnowledgeBaseSection: View {
    let store: StoreOf<SettingsFeature>
    @State private var selectedFolderPath = ""

    var body: some View {
        let state = store.state
        VStack(alignment: .leading, spacing: 0) {

            // Banner
            SectionBanner(
                gradient: VFColor.bannerKBFull,
                title: "Kod tabanınızı tanısın",
                subtitle: "Klasör ekleyin; class/method isimleri otomatik sözlüğe eklenir.",
                iconName: "books.vertical"
            )

        VStack(alignment: .leading, spacing: 28) {
            Spacer().frame(height: 4)

            // Öğrenilen proje terimleri
            SettingsCardSection(title: "Proje Terimleri") {
                HStack(spacing: 10) {
                    Image(systemName: state.contextChunkCount > 0 ? VFIcon.checkFill : VFIcon.circle)
                        .foregroundStyle(state.contextChunkCount > 0 ? VFColor.success : Color.secondary)
                    Text(state.contextChunkCount > 0
                         ? "\(state.contextChunkCount) terim tanınıyor"
                         : "Henüz proje eklenmedi")
                        .font(.system(size: 13))
                        .foregroundStyle(state.contextChunkCount > 0 ? .primary : .secondary)
                    Spacer()
                    if state.contextChunkCount > 0 {
                        Button("Temizle") { store.send(.clearContext) }
                            .buttonStyle(.plain).foregroundStyle(VFColor.destructive).font(.caption)
                    }
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 14)
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

            InfoNote(icon: "info.circle", text: "Kod tabanı taranır; class/struct/func isimlerinin söyleniş biçimleri sözlüğe eklenir (örn. \"apvyumodel\" → AppViewModel).", color: .secondary)

            Spacer()
        }
        .padding(VFSpacing.xxxl)

        } // end outer VStack
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
