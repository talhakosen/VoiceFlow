import SwiftUI
import AppKit

// MARK: - ITDatasetView
// Standalone sentence recording screen. Launched from menu bar, not Settings.
// "Yeni" tab: big card with random unrecorded sentence + mic + shuffle.
// "Pratik" tab: list of recorded sentences.

struct ITDatasetView: View {
    var viewModel: AppViewModel

    @State private var selectedTab: Int = 0
    @State private var totalSentences: Int = 0
    @State private var recordedCount: Int = 0

    var body: some View {
        VStack(spacing: 0) {
            // Top progress bar
            progressHeader
                .padding(.horizontal, 20)
                .padding(.top, 16)
                .padding(.bottom, 8)

            // Tab picker
            Picker("", selection: $selectedTab) {
                Text("Yeni").tag(0)
                Text("Pratik").tag(1)
            }
            .pickerStyle(.segmented)
            .padding(.horizontal, 20)
            .padding(.bottom, 12)

            Divider()

            // Content
            if selectedTab == 0 {
                NewSentenceTab(viewModel: viewModel, totalSentences: $totalSentences, recordedCount: $recordedCount)
            } else {
                PracticedTab(viewModel: viewModel, recordedCount: $recordedCount)
            }
        }
        .frame(width: 520, height: 560)
        .background(Color(NSColor.windowBackgroundColor))
    }

    private var progressHeader: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text("Ses Egitimi")
                    .font(.title3.weight(.semibold))
                Spacer()
                if totalSentences > 0 {
                    Text("\(recordedCount) / \(totalSentences) cumle")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            if totalSentences > 0 {
                ProgressView(value: Double(recordedCount), total: Double(totalSentences))
                    .tint(.green)
            }
        }
    }
}

// MARK: - New Sentence Tab

private struct NewSentenceTab: View {
    var viewModel: AppViewModel
    @Binding var totalSentences: Int
    @Binding var recordedCount: Int

    @State private var currentIndex: Int = -1
    @State private var currentSentence: String = ""
    @State private var recordings: [(whisper: String, wavPath: String)] = []
    @State private var isLoading = false
    @State private var playingIndex: Int? = nil
    @State private var currentSound: NSSound? = nil

    var body: some View {
        VStack(spacing: 0) {
            if isLoading {
                Spacer()
                ProgressView("Yukleniyor...")
                Spacer()
            } else if currentSentence.isEmpty {
                emptyState
            } else {
                sentenceCard
                    .padding(.horizontal, 20)
                    .padding(.top, 20)

                recordingsList
                    .padding(.horizontal, 20)
                    .padding(.top, 8)

                Spacer()

                micButton
                    .padding(.bottom, 24)
            }
        }
        .onAppear {
            viewModel.itDatasetActive = true
            Task { await loadRandom() }
        }
        .onDisappear {
            viewModel.itDatasetActive = false
            viewModel.itDatasetCurrentIndex = -1
            currentSound?.stop()
        }
        .onChange(of: viewModel.itDatasetLastWhisper) {
            if !viewModel.itDatasetLastWhisper.isEmpty {
                recordings.append((whisper: viewModel.itDatasetLastWhisper, wavPath: viewModel.itDatasetLastWavPath))
                viewModel.itDatasetLastWhisper = ""
                viewModel.itDatasetLastWavPath = ""
                recordedCount += 1
            }
        }
    }

    private var emptyState: some View {
        VStack(spacing: 16) {
            Spacer()
            Image(systemName: "checkmark.seal.fill")
                .font(.system(size: 48))
                .foregroundStyle(.green)
            Text("Tum cumleler kaydedildi!")
                .font(.title3.weight(.medium))
            Text("Harika is cikardin.")
                .foregroundStyle(.secondary)
            Spacer()
        }
    }

    private var sentenceCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(currentSentence)
                .font(.system(size: 18, weight: .medium))
                .lineSpacing(4)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(20)
                .background(Color.accentColor.opacity(0.07))
                .clipShape(RoundedRectangle(cornerRadius: 14))

            HStack {
                if !recordings.isEmpty {
                    Label("\(recordings.count) kayit", systemImage: "checkmark.circle.fill")
                        .font(.caption)
                        .foregroundStyle(.green)
                }
                Spacer()
                Button {
                    currentSound?.stop()
                    currentSound = nil
                    playingIndex = nil
                    Task { await loadRandom() }
                } label: {
                    Label("Farkli cumle", systemImage: "shuffle")
                        .font(.caption)
                }
                .buttonStyle(.bordered)
                .controlSize(.small)
                .disabled(isLoading)
            }
        }
    }

    @ViewBuilder
    private var recordingsList: some View {
        if !recordings.isEmpty {
            VStack(spacing: 4) {
                ForEach(Array(recordings.enumerated()), id: \.offset) { i, rec in
                    recordingRow(index: i, rec: rec)
                }
            }
        }
    }

    private func recordingRow(index i: Int, rec: (whisper: String, wavPath: String)) -> some View {
        HStack(spacing: 8) {
            Button {
                if playingIndex == i {
                    currentSound?.stop(); currentSound = nil; playingIndex = nil
                } else if !rec.wavPath.isEmpty {
                    currentSound?.stop()
                    let s = NSSound(contentsOfFile: rec.wavPath, byReference: true)
                    s?.play(); currentSound = s; playingIndex = i
                }
            } label: {
                let isPlaying = playingIndex == i
                Image(systemName: isPlaying ? "stop.circle.fill" : "play.circle.fill")
                    .foregroundStyle(rec.wavPath.isEmpty ? Color.gray : isPlaying ? Color.red : Color.blue)
            }
            .buttonStyle(.plain)
            .disabled(rec.wavPath.isEmpty)

            Text(rec.whisper.isEmpty ? "(ses kaydı)" : rec.whisper)
                .font(.caption)
                .foregroundStyle(.secondary)
                .lineLimit(1)

            Spacer()

            Button {
                currentSound?.stop(); currentSound = nil; playingIndex = nil
                viewModel.deleteITDatasetPair(wavPath: rec.wavPath)
                recordings.remove(at: i)
                if recordedCount > 0 { recordedCount -= 1 }
            } label: {
                Image(systemName: "trash").font(.caption).foregroundStyle(.red)
            }
            .buttonStyle(.plain)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(Color.green.opacity(0.05))
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }

    private var micButton: some View {
        Button {
            if viewModel.isRecording {
                viewModel.stopRecordingForDataset()
            } else {
                viewModel.startRecordingForDataset()
            }
        } label: {
            ZStack {
                Circle()
                    .fill(viewModel.isRecording ? Color.red : Color.accentColor)
                    .frame(width: 64, height: 64)
                    .shadow(color: (viewModel.isRecording ? Color.red : Color.accentColor).opacity(0.4), radius: 12)
                Image(systemName: viewModel.isRecording ? "stop.fill" : "mic.fill")
                    .font(.system(size: 24, weight: .semibold))
                    .foregroundStyle(.white)
            }
        }
        .buttonStyle(.plain)
        .scaleEffect(viewModel.isRecording ? 1.1 : 1.0)
        .animation(.spring(response: 0.3), value: viewModel.isRecording)
    }

    private func loadRandom() async {
        isLoading = true
        defer { isLoading = false }
        do {
            let data = try await viewModel.getITDatasetRandom()
            currentIndex = data.index
            if totalSentences == 0 { totalSentences = data.total }
            currentSentence = data.sentence
            recordings = (data.recordings ?? []).map { (whisper: $0.whisper, wavPath: $0.wavPath) }
            viewModel.itDatasetCurrentIndex = data.index
            viewModel.itDatasetLastWhisper = ""
        } catch {
            print("IT random load error: \(error)")
        }
    }
}

// MARK: - Practiced Tab

private struct PracticedTab: View {
    var viewModel: AppViewModel
    @Binding var recordedCount: Int

    @State private var items: [ITDatasetResponse] = []
    @State private var selected: ITDatasetResponse? = nil
    @State private var isLoading = false

    var body: some View {
        Group {
            if isLoading {
                VStack { Spacer(); ProgressView("Yukleniyor..."); Spacer() }
            } else if items.isEmpty {
                VStack(spacing: 12) {
                    Spacer()
                    Image(systemName: "waveform.slash").font(.system(size: 36)).foregroundStyle(.secondary)
                    Text("Henuz kayit yok").foregroundStyle(.secondary)
                    Text("\"Yeni\" sekmesinden cumle kaydet.").font(.caption).foregroundStyle(.tertiary)
                    Spacer()
                }
            } else if let sel = selected {
                PracticeDetailCard(item: sel, viewModel: viewModel) {
                    selected = nil
                    Task { await loadRecorded() }
                }
                .padding(20)
            } else {
                recordedList
            }
        }
        .onAppear { Task { await loadRecorded() } }
    }

    private var recordedList: some View {
        ScrollView {
            LazyVStack(spacing: 6) {
                ForEach(items, id: \.index) { item in
                    Button { selected = item } label: {
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(item.sentence)
                                    .font(.system(size: 13))
                                    .lineLimit(2)
                                    .multilineTextAlignment(.leading)
                                Text("\(item.recordings?.count ?? 0) kayit")
                                    .font(.caption2)
                                    .foregroundStyle(.green)
                            }
                            Spacer()
                            Image(systemName: "chevron.right")
                                .font(.caption)
                                .foregroundStyle(.tertiary)
                        }
                        .padding(12)
                        .background(Color(NSColor.controlBackgroundColor))
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
        }
    }

    private func loadRecorded() async {
        isLoading = true
        defer { isLoading = false }
        do {
            items = try await viewModel.getITDatasetRecorded()
            recordedCount = items.count
        } catch {
            print("IT recorded load error: \(error)")
        }
    }
}

// MARK: - Practice Detail Card

private struct PracticeDetailCard: View {
    let item: ITDatasetResponse
    var viewModel: AppViewModel
    var onBack: () -> Void

    @State private var playingIndex: Int? = nil
    @State private var currentSound: NSSound? = nil

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Button { onBack() } label: {
                Label("Listeye don", systemImage: "chevron.left")
                    .font(.caption)
            }
            .buttonStyle(.plain)
            .foregroundStyle(Color.accentColor)

            Text(item.sentence)
                .font(.system(size: 16, weight: .medium))
                .padding(16)
                .background(Color.accentColor.opacity(0.07))
                .clipShape(RoundedRectangle(cornerRadius: 12))

            Text("Kayitlar")
                .font(.caption.weight(.semibold))
                .foregroundStyle(.secondary)

            ForEach(Array((item.recordings ?? []).enumerated()), id: \.offset) { i, rec in
                HStack(spacing: 10) {
                    Button {
                        if playingIndex == i {
                            currentSound?.stop(); currentSound = nil; playingIndex = nil
                        } else if !rec.wavPath.isEmpty {
                            currentSound?.stop()
                            let s = NSSound(contentsOfFile: rec.wavPath, byReference: true)
                            s?.play(); currentSound = s; playingIndex = i
                        }
                    } label: {
                        Image(systemName: playingIndex == i ? "stop.circle.fill" : "play.circle.fill")
                            .font(.title3)
                            .foregroundStyle(rec.wavPath.isEmpty ? .gray : playingIndex == i ? .red : .blue)
                    }
                    .buttonStyle(.plain)
                    .disabled(rec.wavPath.isEmpty)

                    VStack(alignment: .leading, spacing: 2) {
                        Text("Varyasyon \(i + 1)").font(.caption2).foregroundStyle(.secondary)
                        Text(rec.whisper.isEmpty ? "(ses kaydi)" : rec.whisper).font(.caption).lineLimit(2)
                    }
                    Spacer()
                    Button {
                        currentSound?.stop(); currentSound = nil; playingIndex = nil
                        viewModel.deleteITDatasetPair(wavPath: rec.wavPath)
                    } label: {
                        Image(systemName: "trash").font(.caption).foregroundStyle(.red)
                    }
                    .buttonStyle(.plain)
                }
                .padding(10)
                .background(Color.green.opacity(0.05))
                .clipShape(RoundedRectangle(cornerRadius: 8))
            }

            Spacer()
        }
        .onDisappear { currentSound?.stop() }
    }
}

// MARK: - Window Controller

final class ITDatasetWindowController: NSObject {
    private var window: NSWindow?

    func open(viewModel: AppViewModel) {
        if let w = window, w.isVisible { w.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps: true); return }
        let hosting = NSHostingController(rootView: ITDatasetView(viewModel: viewModel))
        let w = NSPanel(
            contentRect: NSRect(x: 0, y: 0, width: 520, height: 560),
            styleMask: [.titled, .closable, .nonactivatingPanel],
            backing: .buffered,
            defer: false
        )
        w.contentViewController = hosting
        w.title = "Ses Egitimi"
        w.isFloatingPanel = true
        w.level = .floating
        w.center()
        w.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        window = w
    }
}
