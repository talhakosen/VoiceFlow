import SwiftUI
import AppKit

// MARK: - Word token model

private struct WordToken: Identifiable {
    let id = UUID()
    let original: String
    var text: String
    var isWrong = false
}

// MARK: - TrainingPillView

struct TrainingPillView: View {
    var viewModel: AppViewModel

    @State private var tokens: [WordToken] = []

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            // Header
            HStack(spacing: 6) {
                Image(systemName: "waveform.badge.mic")
                    .foregroundStyle(.secondary)
                Text("Transkripsiyon doğru mu?")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(.primary)
                Spacer()
                Button {
                    viewModel.dismissFeedback()
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 11))
                        .foregroundStyle(.tertiary)
                }
                .buttonStyle(.plain)
            }

            // Word chips
            wordChipsView

            // Hint
            Text("Yanlış kelimeye tıkla → kırmızı. Tekrar tıkla → düzelt.")
                .font(.system(size: 10))
                .foregroundStyle(.tertiary)

            // Bottom bar
            HStack {
                Spacer()
                Button {
                    submitFeedback()
                } label: {
                    Text("Onayla ✓")
                        .font(.system(size: 12, weight: .semibold))
                        .padding(.horizontal, 16)
                        .padding(.vertical, 5)
                }
                .buttonStyle(.borderedProminent)
                .tint(.green)
            }
        }
        .padding(14)
        .frame(minWidth: 500, maxWidth: 700)
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .shadow(color: .black.opacity(0.2), radius: 16, x: 0, y: 4)
        .padding(16)
        .onAppear {
            let text = viewModel.trainingPillResult?.text ?? ""
            tokens = text.components(separatedBy: " ")
                .filter { !$0.isEmpty }
                .map { WordToken(original: $0, text: $0) }
        }
    }

    // MARK: - Word chips

    private var wordChipsView: some View {
        FlowLayout(spacing: 5) {
            ForEach(tokens.indices, id: \.self) { idx in
                chipView(token: tokens[idx])
                    .onTapGesture {
                        if tokens[idx].isWrong {
                            showEditDialog(for: idx)
                        } else {
                            tokens[idx].isWrong = true
                        }
                    }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    @ViewBuilder
    private func chipView(token: WordToken) -> some View {
        let isEdited = token.text != token.original
        let bg: Color = isEdited ? .green.opacity(0.12) : token.isWrong ? .red.opacity(0.08) : .secondary.opacity(0.1)
        let border: Color = isEdited ? .green.opacity(0.3) : token.isWrong ? .red.opacity(0.25) : .clear

        Text(token.text)
            .font(.system(size: 12))
            .foregroundStyle(token.isWrong && !isEdited ? Color.red.opacity(0.7) : Color.primary)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(bg)
            .clipShape(RoundedRectangle(cornerRadius: 6))
            .overlay(RoundedRectangle(cornerRadius: 6).stroke(border, lineWidth: 1))
    }

    // MARK: - Edit dialog (NSAlert — keyboard guaranteed)

    private func showEditDialog(for idx: Int) {
        NSApp.activate(ignoringOtherApps: true)

        let alert = NSAlert()
        alert.messageText = "Kelimeyi düzelt"
        alert.informativeText = "Orijinal: \"\(tokens[idx].original)\""
        alert.addButton(withTitle: "Uygula")
        alert.addButton(withTitle: "İptal")

        let tf = NSTextField(frame: NSRect(x: 0, y: 0, width: 280, height: 24))
        tf.stringValue = tokens[idx].text
        tf.placeholderString = "Doğru yazım..."
        alert.accessoryView = tf
        alert.window.initialFirstResponder = tf
        alert.window.level = .floating + 1

        let response = alert.runModal()
        if response == .alertFirstButtonReturn {
            let trimmed = tf.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
            if !trimmed.isEmpty {
                tokens[idx].text = trimmed
                tokens[idx].isWrong = false
            }
        }
    }

    // MARK: - Dictionary auto-add

    private func addWordCorrectionsToDictionary() {
        // For each token where text ≠ original, add a personal dictionary entry
        let corrections = tokens.filter { $0.text != $0.original && !$0.text.isEmpty }
        for token in corrections {
            viewModel.addDictionaryEntry(
                trigger: token.original.lowercased(),
                replacement: token.text,
                scope: "personal"
            )
        }
    }

    // MARK: - Submit

    private func submitFeedback() {
        let originalText = viewModel.trainingPillResult?.text ?? ""
        let correctedText = tokens.map(\.text).joined(separator: " ")
        let hasEdits = correctedText != originalText
        let hasWrongMarks = tokens.contains { $0.isWrong && $0.text == $0.original }

        if hasEdits {
            Task {
                await viewModel.editFeedback(corrected: correctedText)
            }
            addWordCorrectionsToDictionary()
        } else if hasWrongMarks {
            let wrongWords = tokens.filter { $0.isWrong }.map(\.text).joined(separator: ", ")
            Task { await viewModel.editFeedback(corrected: "__wrong_words__: \(wrongWords)") }
        } else {
            Task { await viewModel.approveFeedback() }
        }
    }
}

// MARK: - FlowLayout (word wrap)

private struct FlowLayout: Layout {
    var spacing: CGFloat = 6

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let width = proposal.width ?? 400
        var x: CGFloat = 0
        var y: CGFloat = 0
        var rowH: CGFloat = 0
        for view in subviews {
            let size = view.sizeThatFits(.unspecified)
            if x + size.width > width && x > 0 { x = 0; y += rowH + spacing; rowH = 0 }
            x += size.width + spacing
            rowH = max(rowH, size.height)
        }
        return CGSize(width: width, height: y + rowH)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        var x = bounds.minX
        var y = bounds.minY
        var rowH: CGFloat = 0
        for view in subviews {
            let size = view.sizeThatFits(.unspecified)
            if x + size.width > bounds.maxX && x > bounds.minX { x = bounds.minX; y += rowH + spacing; rowH = 0 }
            view.place(at: CGPoint(x: x, y: y), proposal: ProposedViewSize(size))
            x += size.width + spacing
            rowH = max(rowH, size.height)
        }
    }
}

// MARK: - TrainingPillWindowController

final class TrainingPillWindowController: NSObject {
    private var panel: NSPanel?
    private var hostingView: NSHostingView<TrainingPillView>?

    func show(viewModel: AppViewModel) {
        guard panel == nil else { return }

        let hosting = NSHostingView(rootView: TrainingPillView(viewModel: viewModel))
        hosting.sizingOptions = [.preferredContentSize]
        hostingView = hosting

        let p = NSPanel(
            contentRect: NSRect(x: 0, y: 0, width: 640, height: 200),
            styleMask: [.borderless, .nonactivatingPanel],
            backing: .buffered,
            defer: false
        )
        p.isFloatingPanel = true
        p.level = .floating
        p.backgroundColor = .clear
        p.isOpaque = false
        p.hasShadow = false
        p.contentView = hosting
        p.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]

        if let screen = NSScreen.main {
            let sw = screen.visibleFrame
            p.setFrameOrigin(NSPoint(x: sw.midX - p.frame.width / 2, y: sw.minY + 32))
        }

        p.orderFront(nil)
        panel = p
    }

    func close() {
        panel?.orderOut(nil)
        panel = nil
        hostingView = nil
    }
}
