import ComposableArchitecture
import SwiftUI
import AppKit

// MARK: - HomeSection

struct HomeSection: View {
    let store: StoreOf<AppFeature>

    @State private var historyItems: [HistoryItem] = []
    @State private var isLoading = false
    @State private var copiedId: Int?

    // HistoryItem.corrected is Bool (true = LLM-corrected), .text = final text, .rawText = raw whisper

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            SectionBanner(
                gradient: VFColor.bannerHomeFull,
                title: "Son Transkripsiyonlarınız",
                subtitle: "VoiceFlow her kaydı güvenle saklar. Fn × 2 ile yeni kayıt başlatın.",
                iconName: "waveform"
            )
            contentArea
        }
        .task(id: store.recording.whisperModelName) { await loadHistory() }
    }

    @ViewBuilder
    private var contentArea: some View {
        VStack(alignment: .leading, spacing: 24) {
            statsRow
            historyCard
        }
        .padding(.horizontal, 20)
        .padding(.top, 20)
        .padding(.bottom, 20)
    }

    private var statsRow: some View {
        let correctedCount = historyItems.filter { $0.corrected }.count
        return HStack(spacing: 12) {
            QuickStatCard(icon: "waveform.circle.fill", label: "Toplam Kayıt", value: "\(historyItems.count)", color: .blue)
            QuickStatCard(icon: "checkmark.seal.fill", label: "Düzeltilmiş", value: "\(correctedCount)", color: .green)
        }
    }

    @ViewBuilder
    private var historyCard: some View {
        SettingsCardSection(title: "Son Transkripsiyonlar") {
            if isLoading {
                loadingRow
            } else if historyItems.isEmpty {
                emptyRow
            } else {
                historyRows
            }
        }
    }

    private var loadingRow: some View {
        HStack {
            ProgressView().scaleEffect(0.8)
            Text("Yükleniyor…").foregroundStyle(.secondary).font(.caption)
        }
        .padding(16)
    }

    private var emptyRow: some View {
        HStack(spacing: 10) {
            Image(systemName: "mic.slash").foregroundStyle(.tertiary)
            Text("Henüz transkripsiyon yok. Fn × 2 ile kayıt başlatın.")
                .foregroundStyle(.secondary)
                .font(.system(size: 13))
            Spacer()
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 14)
    }

    @ViewBuilder
    private var historyRows: some View {
        let limited = Array(historyItems.prefix(20))
        ForEach(Array(limited.enumerated()), id: \.element.id) { idx, item in
            HomeHistoryRow(
                item: item,
                isCopied: copiedId == item.id,
                isLast: idx == limited.count - 1,
                onCopy: { copyItem(item) },
                onCopyRaw: item.corrected ? { copyRaw(item) } : nil,
                onDelete: { Task { await deleteItem(item) } }
            )
        }
        if historyItems.count > 20 {
            Divider().padding(.leading, 16)
            Text("+ \(historyItems.count - 20) daha fazla")
                .font(.caption)
                .foregroundStyle(.tertiary)
                .padding(.horizontal, 16)
                .padding(.vertical, 10)
        }
    }

    private func copyItem(_ item: HistoryItem) {
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(item.text, forType: .string)
        copiedId = item.id
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
            if copiedId == item.id { copiedId = nil }
        }
    }

    private func copyRaw(_ item: HistoryItem) {
        let raw = item.rawText?.isEmpty == false ? item.rawText! : item.text
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(raw, forType: .string)
    }

    private func deleteItem(_ item: HistoryItem) async {
        let baseURL = UserDefaults.standard.string(forKey: AppSettings.serverURL) ?? AppConstants.defaultLocalURL
        guard let url = URL(string: "\(baseURL)/api/history/\(item.id)") else { return }
        var req = URLRequest(url: url)
        req.httpMethod = "DELETE"
        _ = try? await URLSession.shared.data(for: req)
        await MainActor.run {
            historyItems.removeAll { $0.id == item.id }
        }
    }

    private func loadHistory() async {
        isLoading = true
        do {
            let baseURL = UserDefaults.standard.string(forKey: AppSettings.serverURL) ?? AppConstants.defaultLocalURL
            let url = URL(string: "\(baseURL)/api/history?limit=50")!
            let (data, _) = try await URLSession.shared.data(from: url)
            let resp = try JSONDecoder().decode(HistoryResponse.self, from: data)
            await MainActor.run { historyItems = resp.items }
        } catch {
            BackendService.debugLog("HomeSection.loadHistory error: \(error)")
        }
        await MainActor.run { isLoading = false }
    }
}

// MARK: - QuickStatCard

private struct QuickStatCard: View {
    let icon: String
    let label: String
    let value: String
    let color: Color

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .font(.system(size: 22))
                .foregroundStyle(color)
            VStack(alignment: .leading, spacing: 2) {
                Text(value)
                    .font(.system(size: 20, weight: .bold))
                Text(label)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 14)
        .background(Color(nsColor: .controlBackgroundColor))
        .clipShape(RoundedRectangle(cornerRadius: VFRadius.lg))
        .overlay(
            RoundedRectangle(cornerRadius: VFRadius.lg)
                .strokeBorder(Color.primary.opacity(0.07), lineWidth: 1)
        )
        .frame(maxWidth: .infinity)
    }
}

// MARK: - HomeHistoryRow

private struct HomeHistoryRow: View {
    let item: HistoryItem
    let isCopied: Bool
    let isLast: Bool
    let onCopy: () -> Void
    let onCopyRaw: (() -> Void)?
    let onDelete: () -> Void

    private var timeLabel: String {
        let iso = ISO8601DateFormatter()
        iso.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        let date = iso.date(from: item.createdAt) ?? Date()
        let formatter = RelativeDateTimeFormatter()
        formatter.locale = Locale(identifier: "tr_TR")
        formatter.unitsStyle = .abbreviated
        return formatter.localizedString(for: date, relativeTo: Date())
    }

    var body: some View {
        VStack(spacing: 0) {
            HStack(alignment: .top, spacing: 10) {
                // ── Metin + meta ──────────────────────────────────────────
                VStack(alignment: .leading, spacing: 4) {
                    Text(item.text)
                        .font(.system(size: 13))
                        .lineLimit(2)
                        .foregroundStyle(.primary)

                    HStack(spacing: 6) {
                        Text(timeLabel)
                            .font(.caption2)
                            .foregroundStyle(.tertiary)
                        if item.corrected {
                            Text("·").font(.caption2).foregroundStyle(.quaternary)
                            Text("Düzeltildi")
                                .font(.caption2)
                                .foregroundStyle(VFColor.badgeLLM.opacity(0.8))
                        }
                    }
                }

                Spacer()

                // ── Aksiyon butonları ─────────────────────────────────────
                HStack(spacing: 4) {
                    // Kopyala
                    RowIconButton(
                        icon: isCopied ? VFIcon.checkFill : VFIcon.copy,
                        color: isCopied ? VFColor.success : .secondary,
                        help: "Kopyala",
                        action: onCopy
                    )

                    // ⋯ Daha fazla
                    Menu {
                        if let copyRaw = onCopyRaw {
                            Button {
                                copyRaw()
                            } label: {
                                Label("Ham Metni Kopyala", systemImage: "doc.on.doc")
                            }
                            Divider()
                        }

                        Button(role: .destructive) {
                            onDelete()
                        } label: {
                            Label("Sil", systemImage: "trash")
                        }
                    } label: {
                        Image(systemName: "ellipsis")
                            .font(.system(size: 13))
                            .foregroundStyle(.secondary)
                            .frame(width: 24, height: 24)
                            .contentShape(Rectangle())
                    }
                    .menuStyle(.borderlessButton)
                    .fixedSize()
                    .help("Daha fazla")
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 11)

            if !isLast { Divider().padding(.leading, 16) }
        }
    }
}

private struct RowIconButton: View {
    let icon: String
    let color: Color
    let help: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Image(systemName: icon)
                .font(.system(size: 13))
                .foregroundStyle(color)
                .frame(width: 24, height: 24)
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .help(help)
    }
}
