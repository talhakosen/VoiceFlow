import SwiftUI

struct HistoryView: View {
    var viewModel: AppViewModel
    @State private var items: [HistoryItem] = []
    @State private var isLoading = false
    @State private var copiedId: Int?

    private let timeFormatter: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "HH:mm:ss"
        return f
    }()

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Text("Transcription History")
                    .font(VFFont.headline)
                Spacer()
                if !items.isEmpty {
                    Button("Clear All") { Task { await clearAll() } }
                        .buttonStyle(.plain)
                        .foregroundColor(VFColor.destructive)
                        .font(VFFont.caption)
                }
            }
            .padding(.horizontal, VFSpacing.xxl)
            .padding(.vertical, VFSpacing.xl)

            Divider()

            if isLoading {
                Spacer()
                ProgressView()
                Spacer()
            } else if items.isEmpty {
                Spacer()
                Text("No transcriptions yet")
                    .foregroundColor(.secondary)
                    .font(VFFont.subheadline)
                Spacer()
            } else {
                ScrollView {
                    LazyVStack(spacing: 0) {
                        ForEach(items) { item in
                            HistoryRow(
                                item: item,
                                isCopied: copiedId == item.id,
                                onCopy: { text in
                                    NSPasteboard.general.clearContents()
                                    NSPasteboard.general.setString(text, forType: .string)
                                    copiedId = item.id
                                    DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
                                        if copiedId == item.id { copiedId = nil }
                                    }
                                }
                            )
                            Divider().padding(.leading, VFSpacing.xxl)
                        }
                    }
                }
            }
        }
        .frame(width: VFLayout.WindowSize.history.width, height: VFLayout.WindowSize.history.height)
        .task { await loadHistory() }
    }

    private func loadHistory() async {
        isLoading = true
        if let fetched = try? await BackendService().getHistory(limit: 100) {
            items = fetched
        }
        isLoading = false
    }

    private func clearAll() async {
        try? await BackendService().clearHistory()
        items = []
    }
}

struct HistoryRow: View {
    let item: HistoryItem
    let isCopied: Bool
    let onCopy: (String) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: VFSpacing.xs) {
            HStack(spacing: VFSpacing.sm) {
                Text(item.corrected ? "LLM" : "Raw")
                    .font(VFFont.badge)
                    .foregroundColor(.white)
                    .padding(.horizontal, VFSpacing.sm)
                    .padding(.vertical, VFSpacing.xxs)
                    .background(item.corrected ? VFColor.badgeLLM : VFColor.badgeRaw)
                    .cornerRadius(VFRadius.sm)

                if let mode = item.mode {
                    Text(mode)
                        .font(VFFont.badgeMode)
                        .foregroundStyle(.secondary)
                }

                Text(item.createdAt)
                    .font(VFFont.caption)
                    .foregroundColor(.secondary)

                Spacer()

                Button(action: { onCopy(item.text) }) {
                    Text(isCopied ? "Copied!" : "Copy")
                        .font(VFFont.caption)
                        .foregroundColor(isCopied ? VFColor.success : VFColor.primary)
                }
                .buttonStyle(.plain)
            }

            Text(item.text)
                .font(VFFont.historyItem)
                .lineLimit(3)
                .frame(maxWidth: .infinity, alignment: .leading)

            if item.corrected, let raw = item.rawText, raw != item.text {
                Text("Raw: \(raw)")
                    .font(VFFont.historyRaw)
                    .foregroundColor(.secondary)
                    .lineLimit(2)
            }
        }
        .padding(.horizontal, VFSpacing.xxl)
        .padding(.vertical, VFSpacing.lg)
        .contentShape(Rectangle())
        .onTapGesture { onCopy(item.text) }
    }
}
