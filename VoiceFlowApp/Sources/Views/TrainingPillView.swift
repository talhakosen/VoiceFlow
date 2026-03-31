import SwiftUI
import AppKit

// MARK: - Word token model

private struct WordToken: Identifiable {
    let id = UUID()
    let original: String      // never changes — original model output
    var text: String          // may be edited by user
    var isWrong = false       // single tap = marked wrong
    var isEditing = false     // double tap = edit mode
    var editBuffer = ""
}

// MARK: - TrainingPillView

/// Floating feedback panel shown after paste when Training Mode is enabled.
/// Displays transcription as word chips — tap any word to correct it inline.
/// Auto-dismisses after 15 seconds (timer resets on any interaction).
struct TrainingPillView: View {
    var viewModel: AppViewModel

    @State private var tokens: [WordToken] = []
    @State private var confirmed = false

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
            Text("Yanlış kelimeye tıkla ve düzelt. Dokunmadan bırakırsan onaylanmış sayılır.")
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
        .frame(width: 460)
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
            ForEach($tokens) { $token in
                if token.isEditing {
                    // Double-tap: inline edit
                    HStack(spacing: 3) {
                        TextField("", text: $token.editBuffer)
                            .font(.system(size: 12))
                            .frame(minWidth: 40, maxWidth: 120)
                            .textFieldStyle(.plain)
                            .padding(.horizontal, 6)
                            .padding(.vertical, 3)
                            .background(Color.orange.opacity(0.15))
                            .clipShape(RoundedRectangle(cornerRadius: 6))
                            .onSubmit { applyEdit(token: &token) }

                        Button { applyEdit(token: &token) } label: {
                            Image(systemName: "checkmark")
                                .font(.system(size: 10, weight: .bold))
                                .foregroundStyle(.green)
                        }.buttonStyle(.plain)

                        Button {
                            token.isEditing = false
                            token.editBuffer = ""
                        } label: {
                            Image(systemName: "xmark")
                                .font(.system(size: 10))
                                .foregroundStyle(.secondary)
                        }.buttonStyle(.plain)
                    }
                } else {
                    // Normal chip
                    chipView(token: token)
                        .onTapGesture(count: 2) {
                            // Double tap → edit
                            closeAllEditing()
                            if let idx = tokens.firstIndex(where: { $0.id == token.id }) {
                                tokens[idx].editBuffer = tokens[idx].text
                                tokens[idx].isEditing = true
                            }
                        }
                        .onTapGesture(count: 1) {
                            // Single tap → toggle wrong
                            if let idx = tokens.firstIndex(where: { $0.id == token.id }) {
                                tokens[idx].isWrong.toggle()
                            }
                        }
                        .help(token.isWrong ? "Çift tıkla ve düzelt, ya da gönder" : "Hatalıysa tıkla")
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    @ViewBuilder
    private func chipView(token: WordToken) -> some View {
        let isEdited = token.text != token.original
        let bg: Color = isEdited ? .green.opacity(0.15) : token.isWrong ? .red.opacity(0.15) : .secondary.opacity(0.1)
        let border: Color = isEdited ? .green.opacity(0.4) : token.isWrong ? .red.opacity(0.4) : .clear

        Text(token.text)
            .font(.system(size: 12))
            .strikethrough(token.isWrong && !isEdited, color: .red.opacity(0.5))
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(bg)
            .clipShape(RoundedRectangle(cornerRadius: 6))
            .overlay(RoundedRectangle(cornerRadius: 6).stroke(border, lineWidth: 1))
    }

    private func closeAllEditing() {
        for i in tokens.indices where tokens[i].isEditing {
            tokens[i].isEditing = false
        }
    }

    private func applyEdit(token: inout WordToken) {
        let trimmed = token.editBuffer.trimmingCharacters(in: .whitespacesAndNewlines)
        if !trimmed.isEmpty {
            token.text = trimmed
        }
        token.isEditing = false
        token.editBuffer = ""
    }

    private func submitFeedback() {
        confirmed = true
        let originalText = viewModel.trainingPillResult?.text ?? ""
        let correctedText = tokens.map(\.text).joined(separator: " ")
        let hasEdits = correctedText != originalText
        let hasWrongMarks = tokens.contains { $0.isWrong && $0.text == $0.original }

        if hasEdits {
            // User edited some words → full correction pair
            Task { await viewModel.editFeedback(corrected: correctedText) }
        } else if hasWrongMarks {
            // User marked words as wrong but didn't edit → partial signal
            let wrongWords = tokens.filter { $0.isWrong }.map(\.text).joined(separator: ", ")
            Task { await viewModel.editFeedback(corrected: "__wrong_words__: \(wrongWords)") }
        } else {
            // All good
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
            if x + size.width > width && x > 0 {
                x = 0
                y += rowH + spacing
                rowH = 0
            }
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
            if x + size.width > bounds.maxX && x > bounds.minX {
                x = bounds.minX
                y += rowH + spacing
                rowH = 0
            }
            view.place(at: CGPoint(x: x, y: y), proposal: ProposedViewSize(size))
            x += size.width + spacing
            rowH = max(rowH, size.height)
        }
    }
}

// MARK: - TrainingPillWindowController

/// NSPanel floating window that hosts TrainingPillView.
/// Positioned at bottom-center of screen to avoid covering active text areas.
/// Note: must only be called from main thread (NSApplicationDelegate guarantees this).
final class TrainingPillWindowController: NSObject {
    private var panel: NSPanel?
    private var hostingView: NSHostingView<TrainingPillView>?

    func show(viewModel: AppViewModel) {
        guard panel == nil else { return }

        let pillView = TrainingPillView(viewModel: viewModel)
        let hosting = NSHostingView(rootView: pillView)
        hosting.sizingOptions = [.preferredContentSize]
        hostingView = hosting

        let p = NSPanel(
            contentRect: NSRect(x: 0, y: 0, width: 492, height: 160),
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

        // Position: bottom-center of screen (avoids covering active text areas)
        if let screen = NSScreen.main {
            let sw = screen.visibleFrame
            let pw = p.frame.width
            p.setFrameOrigin(NSPoint(
                x: sw.midX - pw / 2,
                y: sw.minY + 32
            ))
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
