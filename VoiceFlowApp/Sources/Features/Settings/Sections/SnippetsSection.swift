import SwiftUI
import AppKit

// MARK: - Snippets

struct SnippetsSection: View {
    var settingsVM: SettingsViewModel

    @State private var newTrigger = ""
    @State private var newExpansion = ""
    @State private var newScope = "personal"

    var body: some View {
        VStack(alignment: .leading, spacing: VFSpacing.xxl) {

            VFSectionHeader("Şablon Listesi")
            VFCard {
                if settingsVM.snippetEntries.isEmpty {
                    Text("Henüz şablon yok. Ses kaydında tetikleyici söyleyince şablon yapıştırılır.")
                        .foregroundStyle(.secondary)
                        .font(VFFont.body)
                        .padding(.horizontal, VFSpacing.xxl)
                        .padding(.vertical, VFSpacing.xl)
                } else {
                    ForEach(Array(settingsVM.snippetEntries.enumerated()), id: \.element.id) { idx, entry in
                        HStack(spacing: VFSpacing.md) {
                            Text(entry.triggerPhrase)
                                .frame(minWidth: VFLayout.fieldSmall, alignment: .leading)
                                .font(VFFont.body)
                            Image(systemName: VFIcon.arrow).foregroundStyle(.secondary)
                            Text(entry.expansion)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .lineLimit(2)
                                .font(VFFont.body)
                            Text(entry.scope == "personal" ? "Kişisel" : "Takım")
                                .font(VFFont.caption)
                                .foregroundStyle(.secondary)
                                .frame(width: 60)
                            if entry.scope == "personal" {
                                Button {
                                    settingsVM.deleteSnippet(id: entry.id)
                                } label: {
                                    Image(systemName: VFIcon.delete).foregroundStyle(VFColor.destructive)
                                }
                                .buttonStyle(.plain)
                            }
                        }
                        .padding(.horizontal, VFSpacing.xxl)
                        .padding(.vertical, VFSpacing.xl)
                        if idx < settingsVM.snippetEntries.count - 1 {
                            Divider().padding(.leading, VFSpacing.xxl)
                        }
                    }
                }
            }

            VFSectionHeader("Şablon Ekle")
            VFCard {
                VStack(spacing: 0) {
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
                            settingsVM.addSnippet(triggerPhrase: newTrigger, expansion: newExpansion, scope: newScope)
                            newTrigger = ""
                            newExpansion = ""
                        }
                        .buttonStyle(.borderedProminent)
                        .disabled(newTrigger.isEmpty || newExpansion.isEmpty)
                    }
                    .padding(.horizontal, VFSpacing.xxl)
                    .padding(.vertical, VFSpacing.xl)
                }
            }
            VFInfoRow(icon: "info.circle", text: "Tetikleyici kelime sesi tam eşleştiğinde şablon metnini yapıştırır. Sözlükten sonra, düzeltmeden önce uygulanır.", color: .secondary)
        }
        .padding(VFSpacing.xxxl)
        .onAppear { settingsVM.loadSnippets() }
    }
}
