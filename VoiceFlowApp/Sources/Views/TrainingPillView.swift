import SwiftUI
import AppKit

// MARK: - TrainingPillView
// Simple correction toast: shows transcribed text + approve/edit actions.
// Replaces the word-chip UI — no chips, no FlowLayout, single text field on edit.

struct TrainingPillView: View {
    var viewModel: AppViewModel

    @State private var isEditing = false
    @State private var editedText = ""
    @FocusState private var textFocused: Bool

    private var displayText: String { viewModel.trainingPillResult?.text ?? "" }

    var body: some View {
        Group {
            if isEditing {
                editingRow
            } else {
                viewingRow
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 10)
        .frame(minWidth: 380, maxWidth: 600)
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .shadow(color: .black.opacity(0.18), radius: 14, x: 0, y: 4)
        .padding(12)
        .task {
            // Auto-dismiss after 5 seconds if user doesn't interact
            try? await Task.sleep(nanoseconds: 5_000_000_000)
            if !isEditing {
                viewModel.dismissFeedback()
            }
        }
    }

    // MARK: - Viewing row

    private var viewingRow: some View {
        HStack(spacing: 10) {
            Text(displayText)
                .font(.system(size: 12))
                .foregroundStyle(.secondary)
                .lineLimit(2)
                .truncationMode(.tail)
                .frame(maxWidth: .infinity, alignment: .leading)

            Button("Düzelt") {
                editedText = displayText
                isEditing = true
                textFocused = true
            }
            .buttonStyle(.plain)
            .font(.system(size: 11))
            .foregroundStyle(.secondary)

            Button {
                Task { await viewModel.approveFeedback() }
            } label: {
                Image(systemName: "checkmark")
                    .font(.system(size: 11, weight: .semibold))
            }
            .buttonStyle(.borderedProminent)
            .tint(.green)
            .controlSize(.small)

            Button {
                viewModel.dismissFeedback()
            } label: {
                Image(systemName: "xmark")
                    .font(.system(size: 10))
                    .foregroundStyle(.tertiary)
            }
            .buttonStyle(.plain)
        }
    }

    // MARK: - Editing row

    private var editingRow: some View {
        HStack(spacing: 10) {
            TextField("Düzeltilmiş metin", text: $editedText, axis: .vertical)
                .font(.system(size: 12))
                .textFieldStyle(.plain)
                .focused($textFocused)
                .lineLimit(1...4)
                .frame(maxWidth: .infinity)
                .onSubmit { submitEdit() }

            Button("Kaydet") { submitEdit() }
                .buttonStyle(.borderedProminent)
                .tint(.blue)
                .controlSize(.small)

            Button("İptal") { isEditing = false }
                .buttonStyle(.plain)
                .controlSize(.small)
                .foregroundStyle(.secondary)
        }
    }

    // MARK: - Submit

    private func submitEdit() {
        let original = displayText
        let corrected = editedText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !corrected.isEmpty else { return }
        isEditing = false

        if corrected != original {
            addWordCorrectionsToDictionary(original: original, corrected: corrected)
            Task { await viewModel.editFeedback(corrected: corrected) }
        } else {
            Task { await viewModel.approveFeedback() }
        }
    }

    // Word-level diff: add personal dictionary entries for changed words (same length only)
    private func addWordCorrectionsToDictionary(original: String, corrected: String) {
        let origWords = original.components(separatedBy: .whitespaces).filter { !$0.isEmpty }
        let corrWords = corrected.components(separatedBy: .whitespaces).filter { !$0.isEmpty }
        guard origWords.count == corrWords.count else { return }
        for (orig, corr) in zip(origWords, corrWords) where orig != corr {
            viewModel.addDictionaryEntry(trigger: orig.lowercased(), replacement: corr, scope: "personal")
        }
    }
}

// MARK: - TrainingPillWindowController

final class TrainingPillWindowController: NSObject {
    private var panel: NSPanel?

    func show(viewModel: AppViewModel) {
        guard panel == nil else { return }

        let hosting = NSHostingView(rootView: TrainingPillView(viewModel: viewModel))
        hosting.sizingOptions = [.preferredContentSize]

        let p = NSPanel(
            contentRect: NSRect(x: 0, y: 0, width: 600, height: 60),
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
    }
}
