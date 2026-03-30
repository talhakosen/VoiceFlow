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
                    .font(.headline)
                Spacer()
                if !items.isEmpty {
                    Button("Clear All") { Task { await clearAll() } }
                        .buttonStyle(.plain)
                        .foregroundColor(.red)
                        .font(.caption)
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)

            Divider()

            if isLoading {
                Spacer()
                ProgressView()
                Spacer()
            } else if items.isEmpty {
                Spacer()
                Text("No transcriptions yet")
                    .foregroundColor(.secondary)
                    .font(.subheadline)
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
                            Divider().padding(.leading, 16)
                        }
                    }
                }
            }
        }
        .frame(width: 420, height: 480)
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
        VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 6) {
                Text(item.corrected ? "LLM" : "Raw")
                    .font(.system(size: 10, weight: .semibold))
                    .foregroundColor(.white)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(item.corrected ? Color.green : Color.orange)
                    .cornerRadius(4)

                if let mode = item.mode {
                    Text(mode)
                        .font(.system(size: 9))
                        .foregroundStyle(.secondary)
                }

                Text(item.createdAt)
                    .font(.caption)
                    .foregroundColor(.secondary)

                Spacer()

                Button(action: { onCopy(item.text) }) {
                    Text(isCopied ? "Copied!" : "Copy")
                        .font(.caption)
                        .foregroundColor(isCopied ? .green : .accentColor)
                }
                .buttonStyle(.plain)
            }

            Text(item.text)
                .font(.system(size: 13))
                .lineLimit(3)
                .frame(maxWidth: .infinity, alignment: .leading)

            if item.corrected, let raw = item.rawText, raw != item.text {
                Text("Raw: \(raw)")
                    .font(.system(size: 11))
                    .foregroundColor(.secondary)
                    .lineLimit(2)
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
        .contentShape(Rectangle())
        .onTapGesture { onCopy(item.text) }
    }
}
