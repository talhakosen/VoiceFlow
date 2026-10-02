import ComposableArchitecture
import SwiftUI
import AppKit

// MARK: - Dictionary

struct DictionarySection: View {
    let store: StoreOf<SettingsFeature>

    @State private var selectedTab = 0
    @State private var newTrigger = ""
    @State private var newReplacement = ""

    private enum Tab: Int { case personal, team, learned }
    private var tab: Tab { Tab(rawValue: selectedTab) ?? .personal }

    private var entries: [DictionaryEntry] {
        switch tab {
        case .personal: store.personalEntries
        case .team: store.teamEntries
        case .learned: store.learnedEntries
        }
    }

    private var listTitle: String {
        switch tab {
        case .personal: "Kişisel Kurallar"
        case .team: "Takım Kuralları"
        case .learned: "VoiceFlow'un Öğrendikleri"
        }
    }

    private var emptyText: String {
        switch tab {
        case .personal: "Henüz kişisel kural yok."
        case .team: "Takım kuralı yok. Kişisel kurallarını takıma ekleyebilirsin."
        case .learned: "Henüz öğrenilen kelime yok. Menüden \"Öğrendiklerini Güncelle\" ile son diktelerinden öğrenir."
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {

            // Banner
            SectionBanner(
                gradient: VFColor.bannerDictFull,
                title: "VoiceFlow, sizin gibi konuşur",
                subtitle: "Kişisel ve teknik terimlerinizi ekleyin; doğruluk otomatik artar.",
                iconName: "character.book.closed"
            )

        VStack(alignment: .leading, spacing: 28) {
            Spacer().frame(height: 4)

            // Tab seçici
            Picker("", selection: $selectedTab) {
                Text("Kişisel (\(store.personalEntries.count))").tag(Tab.personal.rawValue)
                Text("Takım (\(store.teamEntries.count))").tag(Tab.team.rawValue)
                Text("Öğrenilen (\(store.learnedEntries.count))").tag(Tab.learned.rawValue)
            }
            .pickerStyle(.segmented)
            .frame(width: 380, alignment: .leading)

            // Liste
            SettingsCardSection(title: listTitle) {
                if entries.isEmpty {
                    Text(emptyText)
                        .foregroundStyle(.secondary)
                        .font(.system(size: 13))
                        .padding(.horizontal, 16)
                        .padding(.vertical, 14)
                } else {
                    ForEach(Array(entries.enumerated()), id: \.element.id) { idx, entry in
                        DictionaryRow(
                            entry: entry,
                            alreadyShared: tab == .personal ? store.state.isSharedWithTeam(entry) : false,
                            isLast: idx == entries.count - 1,
                            onDelete: { store.send(.deleteDictionaryEntry(entry.id)) },
                            onShareToTeam: tab == .personal ? {
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

            if tab == .learned {
                InfoNote(icon: "info.circle", text: "Yanlış öğrenilmiş bir kelimeyi silersen VoiceFlow onu bir daha öğrenmez.", color: .secondary)
            } else {
                // Kural Ekle
                SettingsCardSection(title: tab == .personal ? "Kişisel Kural Ekle" : "Takım Kuralı Ekle") {
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
                                scope: tab == .personal ? "personal" : "team"
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
            }

            Spacer()
        }
        .padding(VFSpacing.xxxl)

        } // end outer VStack
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
