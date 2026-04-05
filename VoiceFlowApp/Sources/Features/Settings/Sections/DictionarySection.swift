import SwiftUI
import AppKit

// MARK: - Dictionary

struct DictionarySection: View {
    var settingsVM: SettingsViewModel

    @State private var selectedTab = 0
    @State private var newTrigger = ""
    @State private var newReplacement = ""

    private var personalEntries: [DictionaryEntry] {
        settingsVM.dictionaryEntries.filter { $0.scope == "personal" }
    }

    private var teamEntries: [DictionaryEntry] {
        settingsVM.dictionaryEntries.filter { $0.scope == "team" }
    }

    private func isSharedWithTeam(_ entry: DictionaryEntry) -> Bool {
        teamEntries.contains { $0.trigger == entry.trigger && $0.replacement == entry.replacement }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: VFSpacing.xxl) {

            // Tab
            Picker("", selection: $selectedTab) {
                Text("Kişisel (\(personalEntries.count))").tag(0)
                Text("Takım (\(teamEntries.count))").tag(1)
            }
            .pickerStyle(.segmented)
            .frame(width: 260, alignment: .leading)

            // Liste
            VFSectionHeader(selectedTab == 0 ? "Kişisel Kurallar" : "Takım Kuralları")
            VFCard {
                let entries = selectedTab == 0 ? personalEntries : teamEntries
                if entries.isEmpty {
                    Text(selectedTab == 0
                         ? "Henüz kişisel kural yok."
                         : "Takım kuralı yok. Kişisel kurallarını takıma ekleyebilirsin.")
                        .foregroundStyle(.secondary)
                        .font(VFFont.body)
                        .padding(.horizontal, VFSpacing.xxl)
                        .padding(.vertical, VFSpacing.xl)
                } else {
                    ForEach(Array(entries.enumerated()), id: \.element.id) { idx, entry in
                        DictionaryRow(
                            entry: entry,
                            alreadyShared: selectedTab == 0 ? isSharedWithTeam(entry) : false,
                            onDelete: { settingsVM.deleteDictionaryEntry(id: entry.id) },
                            onShareToTeam: selectedTab == 0 ? {
                                settingsVM.addDictionaryEntry(
                                    trigger: entry.trigger,
                                    replacement: entry.replacement,
                                    scope: "team"
                                )
                            } : nil
                        )
                        if idx < entries.count - 1 {
                            Divider().padding(.leading, VFSpacing.xxl)
                        }
                    }
                }
            }

            // Kural Ekle
            VFSectionHeader(selectedTab == 0 ? "Kişisel Kural Ekle" : "Takım Kuralı Ekle")
            VFCard {
                VStack(spacing: 0) {
                    HStack(spacing: VFSpacing.md) {
                        TextField("kelime (örn: voisflow)", text: $newTrigger)
                            .textFieldStyle(.roundedBorder)
                        Image(systemName: VFIcon.arrow).foregroundStyle(.secondary)
                        TextField("doğru yazım (örn: VoiceFlow)", text: $newReplacement)
                            .textFieldStyle(.roundedBorder)
                        Button("Ekle") {
                            guard !newTrigger.isEmpty, !newReplacement.isEmpty else { return }
                            let scope = selectedTab == 0 ? "personal" : "team"
                            settingsVM.addDictionaryEntry(trigger: newTrigger, replacement: newReplacement, scope: scope)
                            newTrigger = ""
                            newReplacement = ""
                        }
                        .buttonStyle(.borderedProminent)
                        .disabled(newTrigger.isEmpty || newReplacement.isEmpty)
                    }
                    .padding(.horizontal, VFSpacing.xxl)
                    .padding(.vertical, VFSpacing.xl)
                }
            }
            VFInfoRow(icon: "info.circle", text: "Whisper sonrası, düzeltme öncesi uygulanır. Büyük/küçük harf duyarsız, kelime sınırı korunur.", color: .secondary)
        }
        .padding(VFSpacing.xxxl)
        .onAppear { settingsVM.loadDictionary() }
    }
}

struct DictionaryRow: View {
    let entry: DictionaryEntry
    let alreadyShared: Bool
    let onDelete: () -> Void
    let onShareToTeam: (() -> Void)?

    var body: some View {
        HStack(spacing: VFSpacing.md) {
            Text(entry.trigger)
                .frame(minWidth: VFLayout.fieldSmall, alignment: .leading)
                .foregroundStyle(.primary)
                .font(VFFont.body)
            Image(systemName: VFIcon.arrow)
                .foregroundStyle(.secondary)
                .font(VFFont.caption)
            Text(entry.replacement)
                .frame(maxWidth: .infinity, alignment: .leading)
                .foregroundStyle(.primary)
                .font(VFFont.body)

            if let share = onShareToTeam {
                Button {
                    share()
                } label: {
                    Label(
                        alreadyShared ? "Eklendi" : "Takıma ekle",
                        systemImage: alreadyShared ? VFIcon.checkmark : VFIcon.shareTeam
                    )
                    .font(VFFont.caption)
                    .foregroundStyle(alreadyShared ? Color.secondary : VFColor.primary)
                }
                .buttonStyle(.plain)
                .disabled(alreadyShared)
            }

            Button { onDelete() } label: {
                Image(systemName: VFIcon.delete).foregroundStyle(VFColor.destructive)
            }
            .buttonStyle(.plain)
        }
        .padding(.horizontal, VFSpacing.xxl)
        .padding(.vertical, VFSpacing.xl)
    }
}
