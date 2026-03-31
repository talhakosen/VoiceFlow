import SwiftUI
import AppKit

// MARK: - TrainingSessionView

struct TrainingSessionView: View {

    @State private var vm = TrainingViewModel()

    var body: some View {
        VStack(spacing: 0) {
            headerBar

            Divider()

            Group {
                switch vm.sessionState {
                case .idle, .selectingDomain:
                    domainPickerScreen
                case .loading:
                    loadingScreen
                case .inProgress:
                    sessionScreen(transcribed: nil)
                case .recording:
                    sessionScreen(transcribed: nil)
                case .transcribing:
                    sessionScreen(transcribed: nil)
                case .reviewing(let transcribed):
                    sessionScreen(transcribed: transcribed)
                case .complete(let count, let rate):
                    summaryScreen(count: count, rate: rate)
                case .error(let msg):
                    errorScreen(msg)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .frame(width: 680, height: 520)
    }

    // MARK: - Header

    private var headerBar: some View {
        HStack(spacing: 8) {
            Image(systemName: "brain.head.profile")
                .foregroundStyle(.blue)
                .font(.title3)
            Text("Egitim Oturumu")
                .font(.headline)
            Spacer()

            if case .inProgress = vm.sessionState {
                progressChip
            } else if case .recording = vm.sessionState {
                progressChip
            } else if case .reviewing = vm.sessionState {
                progressChip
            } else if case .transcribing = vm.sessionState {
                progressChip
            }
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 12)
    }

    private var progressChip: some View {
        HStack(spacing: 8) {
            Text(vm.progressLabel)
                .font(.system(.caption, design: .monospaced))
                .foregroundStyle(.secondary)
            ProgressView(value: vm.progress)
                .progressViewStyle(.linear)
                .frame(width: 120)
            Text(vm.correctionRateLabel + " duzeltme")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }

    // MARK: - Domain picker screen

    private var domainPickerScreen: some View {
        VStack(spacing: 28) {
            Spacer()

            VStack(spacing: 8) {
                Image(systemName: "waveform.and.mic")
                    .font(.system(size: 44))
                    .foregroundStyle(.blue.opacity(0.8))
                Text("Egitim Modu")
                    .font(.title2.bold())
                Text("Sesle cumleleri okuyun, Whisper transkripte etsin.\nYanlis kelimeleri duzeltarak kisisel egitim verisi olusturun.")
                    .font(.body)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: 440)
            }

            VStack(alignment: .leading, spacing: 12) {
                Text("Domain Secin")
                    .font(.headline)
                Picker("Domain", selection: $vm.selectedDomain) {
                    Label("Genel", systemImage: "bubble.left.and.bubble.right").tag("general")
                    Label("Muhendislik", systemImage: "cpu").tag("engineering")
                    Label("Ofis / Is", systemImage: "briefcase").tag("office")
                }
                .pickerStyle(.radioGroup)
            }
            .padding(20)
            .background(.fill.opacity(0.4))
            .clipShape(RoundedRectangle(cornerRadius: 10))

            Button {
                vm.startSession()
            } label: {
                Label("Egitim Oturumu Baslat", systemImage: "play.fill")
                    .frame(minWidth: 220)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)

            Spacer()
        }
        .padding(32)
    }

    // MARK: - Loading screen

    private var loadingScreen: some View {
        VStack(spacing: 16) {
            ProgressView()
            Text("Cumleler yukleniyor...")
                .foregroundStyle(.secondary)
        }
    }

    // MARK: - Active session screen

    @ViewBuilder
    private func sessionScreen(transcribed: String?) -> some View {
        VStack(spacing: 20) {
            if let sentence = vm.currentSentence {
                // Sentence card
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Label(sentence.domain, systemImage: domainIcon(sentence.domain))
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        Spacer()
                        Text(sentence.difficulty)
                            .font(.caption)
                            .foregroundStyle(difficultyColor(sentence.difficulty))
                            .padding(.horizontal, 8)
                            .padding(.vertical, 2)
                            .background(difficultyColor(sentence.difficulty).opacity(0.1))
                            .clipShape(Capsule())
                    }

                    Text(sentence.text)
                        .font(.system(size: 18, weight: .medium))
                        .lineSpacing(4)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.vertical, 4)
                }
                .padding(16)
                .background(.fill.opacity(0.5))
                .clipShape(RoundedRectangle(cornerRadius: 12))

                // Recording control
                recordingControl

                // Transcription review (shown after recording stops)
                if let t = transcribed, !t.isEmpty {
                    transcriptionReviewSection(transcribed: t)
                }
            }

            Spacer()

            // Bottom action bar
            HStack {
                Button {
                    vm.skip()
                } label: {
                    Label("Atla", systemImage: "forward.fill")
                }
                .buttonStyle(.bordered)
                .foregroundStyle(.secondary)
                .disabled(vm.isRecording || vm.isTranscribing)

                Spacer()

                if case .reviewing = vm.sessionState {
                    Button {
                        vm.submitAndNext()
                    } label: {
                        Label("Kaydet ve Devam", systemImage: "arrow.right.circle.fill")
                            .frame(minWidth: 160)
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(.green)
                }
            }
        }
        .padding(20)
    }

    private var recordingControl: some View {
        HStack(spacing: 16) {
            if vm.isTranscribing {
                HStack(spacing: 8) {
                    ProgressView().scaleEffect(0.8)
                    Text("Transkribe ediliyor...")
                        .foregroundStyle(.secondary)
                        .font(.callout)
                }
                .frame(maxWidth: .infinity)
            } else if vm.isRecording {
                Button {
                    vm.stopRecordingAndTranscribe()
                } label: {
                    HStack(spacing: 8) {
                        Circle()
                            .fill(.red)
                            .frame(width: 10, height: 10)
                        Text("Kaydi Durdur")
                    }
                    .frame(minWidth: 160)
                }
                .buttonStyle(.borderedProminent)
                .tint(.red)
            } else if case .inProgress = vm.sessionState {
                Button {
                    vm.startRecording()
                } label: {
                    Label("Kayit Al", systemImage: "mic.fill")
                        .frame(minWidth: 160)
                }
                .buttonStyle(.borderedProminent)
                .tint(.blue)
                Text("Cumleyi yukari sesle okuyun, sonra kaydi durdurun.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }

    @ViewBuilder
    private func transcriptionReviewSection(transcribed: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Transkripsiyon")
                .font(.caption)
                .foregroundStyle(.secondary)
            TextEditor(text: $vm.userCorrection)
                .font(.system(size: 14))
                .frame(minHeight: 60, maxHeight: 90)
                .scrollContentBackground(.hidden)
                .padding(8)
                .background(.background.opacity(0.6))
                .clipShape(RoundedRectangle(cornerRadius: 8))
                .overlay(
                    RoundedRectangle(cornerRadius: 8)
                        .stroke(.separator, lineWidth: 1)
                )
            if vm.userCorrection != transcribed {
                HStack(spacing: 4) {
                    Image(systemName: "pencil.circle.fill")
                        .foregroundStyle(.orange)
                    Text("Duzeltme yapildi")
                        .font(.caption)
                        .foregroundStyle(.orange)
                }
            }
        }
    }

    // MARK: - Summary screen

    private func summaryScreen(count: Int, rate: Double) -> some View {
        VStack(spacing: 28) {
            Spacer()

            VStack(spacing: 10) {
                Image(systemName: "checkmark.seal.fill")
                    .font(.system(size: 52))
                    .foregroundStyle(.green)
                Text("Oturum Tamamlandi!")
                    .font(.title2.bold())
            }

            HStack(spacing: 32) {
                statCard(
                    value: "\(count)",
                    label: "Ornek Toplandi",
                    icon: "waveform",
                    color: .blue
                )
                statCard(
                    value: "\(Int(rate * 100))%",
                    label: "Duzeltme Orani",
                    icon: "pencil.circle",
                    color: rate > 0.2 ? .orange : .green
                )
                statCard(
                    value: "\(vm.skippedCount)",
                    label: "Atlanan",
                    icon: "forward",
                    color: .secondary
                )
            }

            Text("Bu veriler correction_feedback tablosuna kaydedildi ve gelecekte model iyilestirmesi icin kullanilacak.")
                .font(.caption)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .frame(maxWidth: 400)

            Button {
                vm.resetToIdle()
            } label: {
                Label("Yeni Oturum Baslat", systemImage: "arrow.counterclockwise")
                    .frame(minWidth: 200)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)

            Spacer()
        }
        .padding(32)
    }

    private func statCard(value: String, label: String, icon: String, color: Color) -> some View {
        VStack(spacing: 8) {
            Image(systemName: icon)
                .font(.title2)
                .foregroundStyle(color)
            Text(value)
                .font(.system(size: 32, weight: .bold, design: .rounded))
                .foregroundStyle(color)
            Text(label)
                .font(.caption)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .frame(width: 120)
        .padding(16)
        .background(.fill.opacity(0.4))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    // MARK: - Error screen

    private func errorScreen(_ message: String) -> some View {
        VStack(spacing: 16) {
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.system(size: 44))
                .foregroundStyle(.orange)
            Text("Hata")
                .font(.title3.bold())
            Text(message)
                .font(.callout)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .frame(maxWidth: 380)
            Button("Tekrar Dene") {
                vm.resetToIdle()
            }
            .buttonStyle(.borderedProminent)
        }
        .padding(32)
    }

    // MARK: - Helpers

    private func domainIcon(_ domain: String) -> String {
        switch domain {
        case "engineering": return "cpu"
        case "office":      return "briefcase"
        default:            return "bubble.left.and.bubble.right"
        }
    }

    private func difficultyColor(_ difficulty: String) -> Color {
        switch difficulty {
        case "easy":   return .green
        case "hard":   return .red
        default:       return .orange
        }
    }
}

// MARK: - TrainingSessionWindowController

final class TrainingSessionWindowController: NSObject {
    private var panel: NSPanel?

    func show() {
        if let existing = panel {
            existing.makeKeyAndOrderFront(nil)
            NSApp.activate(ignoringOtherApps: true)
            return
        }

        let view = TrainingSessionView()
        let hosting = NSHostingView(rootView: view)
        hosting.sizingOptions = [.preferredContentSize]

        let p = NSPanel(
            contentRect: NSRect(x: 0, y: 0, width: 680, height: 520),
            styleMask: [.titled, .closable, .resizable, .nonactivatingPanel],
            backing: .buffered,
            defer: false
        )
        p.title = "Egitim Modu"
        p.isFloatingPanel = true
        p.level = .floating
        p.contentView = hosting
        p.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        p.delegate = self

        if let screen = NSScreen.main {
            let sf = screen.visibleFrame
            p.setFrameOrigin(NSPoint(
                x: sf.midX - p.frame.width / 2,
                y: sf.midY - p.frame.height / 2
            ))
        }

        p.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        panel = p
    }

    func close() {
        panel?.orderOut(nil)
        panel = nil
    }
}

extension TrainingSessionWindowController: NSWindowDelegate {
    func windowWillClose(_ notification: Notification) {
        panel = nil
    }
}
