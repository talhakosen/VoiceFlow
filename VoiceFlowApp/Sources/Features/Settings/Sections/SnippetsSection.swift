import ComposableArchitecture
import SwiftUI
import AppKit

// MARK: - Snippets

struct SnippetsSection: View {
    let store: StoreOf<SettingsFeature>

    @State private var newTrigger = ""
    @State private var newExpansion = ""
    @State private var newScope = "personal"

    var body: some View {
        VStack(alignment: .leading, spacing: 28) {

            Text("Şablonlar")
                .font(.system(size: 22, weight: .bold))
                .padding(.bottom, 4)

            // Liste
            SettingsCardSection(title: "Şablon Listesi") {
                if store.snippetEntries.isEmpty {
                    Text("Henüz şablon yok. Ses kaydında tetikleyici söyleyince şablon yapıştırılır.")
                        .foregroundStyle(.secondary)
                        .font(.system(size: 13))
                        .padding(.horizontal, 16)
                        .padding(.vertical, 14)
                } else {
                    ForEach(Array(store.snippetEntries.enumerated()), id: \.element.id) { idx, entry in
                        let isLast = idx == store.snippetEntries.count - 1
                        VStack(spacing: 0) {
                            HStack(spacing: VFSpacing.md) {
                                Text(entry.triggerPhrase)
                                    .frame(minWidth: VFLayout.fieldSmall, alignment: .leading)
                                    .font(.system(size: 13, weight: .medium))
                                Image(systemName: VFIcon.arrow).foregroundStyle(.secondary).font(.caption)
                                Text(entry.expansion)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                    .lineLimit(2)
                                    .font(.system(size: 13))
                                Text(entry.scope == "personal" ? "Kişisel" : "Takım")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                    .frame(width: 56)
                                if entry.scope == "personal" {
                                    Button {
                                        store.send(.deleteSnippet(entry.id))
                                    } label: {
                                        Image(systemName: VFIcon.delete).foregroundStyle(VFColor.destructive)
                                    }
                                    .buttonStyle(.plain)
                                }
                            }
                            .padding(.horizontal, 16)
                            .padding(.vertical, 11)
                            if !isLast { Divider().padding(.leading, 16) }
                        }
                    }
                }
            }

            // Ekle
            SettingsCardSection(title: "Şablon Ekle") {
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
                        store.send(.addSnippet(trigger: newTrigger, expansion: newExpansion))
                        newTrigger = ""
                        newExpansion = ""
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(newTrigger.isEmpty || newExpansion.isEmpty)
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 14)
            }

            InfoNote(icon: "info.circle", text: "Tetikleyici kelime sesi tam eşleştiğinde şablon metnini yapıştırır. Sözlükten sonra, düzeltmeden önce uygulanır.", color: .secondary)

            Spacer()
        }
        .padding(VFSpacing.xxxl)
        .onAppear { store.send(.loadSnippets) }
    }
}
