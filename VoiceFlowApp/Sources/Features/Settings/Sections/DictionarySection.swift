import ComposableArchitecture
import SwiftUI
import AppKit

// MARK: - Dictionary

struct DictionarySection: View {
    let store: StoreOf<SettingsFeature>

    @State private var selectedTab = 0
    @State private var newTrigger = ""
    @State private var newReplacement = ""

    private var personalEntries: [DictionaryEntry] {
        store.dictionaryEntries.filter { $0.scope == "personal" }
    }
    private var teamEntries: [DictionaryEntry] {
        store.dictionaryEntries.filter { $0.scope == "team" }
    }
    private func isSharedWithTeam(_ entry: DictionaryEntry) -> Bool {
        teamEntries.contains { $0.trigger == entry.trigger && $0.replacement == entry.replacement }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 28) {

            Text("Sözlük")
                .font(.system(size: 22, weight: .bold))
                .padding(.bottom, 4)

            // Tab seçici
            Picker("", selection: $selectedTab) {
                Text("Kişisel (\(personalEntries.count))").tag(0)
                Text("Takım (\(teamEntries.count))").tag(1)
            }
            .pickerStyle(.segmented)
            .frame(width: 260, alignment: .leading)

            // Liste
            SettingsCardSection(title: selectedTab == 0 ? "Kişisel Kurallar" : "Takım Kuralları") {
                let entries = selectedTab == 0 ? personalEntries : teamEntries
                if entries.isEmpty {
                    Text(selectedTab == 0
                         ? "Henüz kişisel kural yok."
                         : "Takım kuralı yok. Kişisel kurallarını takıma ekleyebilirsin.")
                        .foregroundStyle(.secondary)
                        .font(.system(size: 13))
                        .padding(.horizontal, 16)
                        .padding(.vertical, 14)
                } else {
                    ForEach(Array(entries.enumerated()), id: \.element.id) { idx, entry in
                        DictionaryRow(
                            entry: entry,
                            alreadyShared: selectedTab == 0 ? isSharedWithTeam(entry) : false,
                            isLast: idx == entries.count - 1,
                            onDelete: { store.send(.deleteDictionaryEntry(entry.id)) },
                            onShareToTeam: selectedTab == 0 ? {
                                store.send(.addDictionaryEntry(
                                    trigger: entry.trigger,
                                    replacement: entry.replacement,
                                    scope: "team"
                                ))
                            } : nil
                        )
                    }
                }
            }

            // Kural Ekle
            SettingsCardSection(title: selectedTab == 0 ? "Kişisel Kural Ekle" : "Takım Kuralı Ekle") {
                HStack(spacing: VFSpacing.md) {
                    TextField("kelime (örn: voisflow)", text: $newTrigger)
                        .textFieldStyle(.roundedBorder)
                    Image(systemName: VFIcon.arrow).foregroundStyle(.secondary)
                    TextField("doğru yazım (örn: VoiceFlow)", text: $newReplacement)
                        .textFieldStyle(.roundedBorder)
                    Button("Ekle") {
                        guard !newTrigger.isEmpty, !newReplacement.isEmpty else { return }
                        store.send(.addDictionaryEntry(
                            trigger: newTrigger,
                            replacement: newReplacement,
                            scope: selectedTab == 0 ? "personal" : "team"
                        ))
                        newTrigger = ""
                        newReplacement = ""
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(newTrigger.isEmpty || newReplacement.isEmpty)
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 14)
            }

            InfoNote(icon: "info.circle", text: "Whisper sonrası, düzeltme öncesi uygulanır. Büyük/küçük harf duyarsız, kelime sınırı korunur.", color: .secondary)

            Spacer()
        }
        .padding(VFSpacing.xxxl)
        .onAppear { store.send(.loadDictionary) }
    }
}

// MARK: - DictionaryRow

struct DictionaryRow: View {
    let entry: DictionaryEntry
    let alreadyShared: Bool
    let isLast: Bool
    let onDelete: () -> Void
    let onShareToTeam: (() -> Void)?

    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: VFSpacing.md) {
                Text(entry.trigger)
                    .frame(minWidth: VFLayout.fieldSmall, alignment: .leading)
                    .font(.system(size: 13, weight: .medium))
                Image(systemName: VFIcon.arrow).foregroundStyle(.secondary).font(.caption)
                Text(entry.replacement)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .font(.system(size: 13))

                if let share = onShareToTeam {
                    Button {
                        share()
                    } label: {
                        Label(
                            alreadyShared ? "Eklendi" : "Takıma ekle",
                            systemImage: alreadyShared ? VFIcon.checkmark : VFIcon.shareTeam
                        )
                        .font(.caption)
                        .foregroundStyle(alreadyShared ? .secondary : VFColor.primary)
                    }
                    .buttonStyle(.plain)
                    .disabled(alreadyShared)
                }

                Button { onDelete() } label: {
                    Image(systemName: VFIcon.delete).foregroundStyle(VFColor.destructive)
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 11)

            if !isLast { Divider().padding(.leading, 16) }
        }
    }
}
