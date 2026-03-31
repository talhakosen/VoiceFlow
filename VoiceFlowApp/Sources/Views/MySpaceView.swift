import SwiftUI
import AppKit

// MARK: - MySpaceView
// Kullanicinin kisisel alani: taninma skoru, istatistikler, son duzeltmeler, "5 Cumle Soyle" butonu.
// UI'da Whisper / training / model / fine-tune kelimeleri kullanilmaz.

struct MySpaceView: View {

    var viewModel: AppViewModel

    @State private var trainingSessionController = TrainingSessionWindowController()

    var body: some View {
        VStack(spacing: 0) {
            headerBar
            Divider()

            if viewModel.isLoadingMySpace {
                loadingView
            } else if let stats = viewModel.mySpaceStats, stats.totalTranscripts > 0 {
                ScrollView {
                    VStack(spacing: 20) {
                        recognitionScoreRing(score: stats.recognitionScore)
                        statsRow(stats: stats)
                        correctionsSection
                    }
                    .padding(24)
                }
            } else {
                emptyStateView
            }
        }
        .frame(width: 680, height: 560)
        .onAppear { viewModel.loadMySpace() }
    }

    // MARK: - Header

    private var headerBar: some View {
        HStack(spacing: 10) {
            Image(systemName: "person.crop.circle")
                .foregroundStyle(.blue)
                .font(.title3)
            Text("Kisisel Alan")
                .font(.headline)
            Spacer()
            Button {
                viewModel.loadMySpace()
            } label: {
                Image(systemName: "arrow.clockwise")
                    .font(.callout)
            }
            .buttonStyle(.plain)
            .foregroundStyle(.secondary)
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 12)
    }

    // MARK: - Recognition Score Ring

    private func recognitionScoreRing(score: Double) -> some View {
        VStack(spacing: 12) {
            ZStack {
                // Background ring
                Circle()
                    .stroke(Color.secondary.opacity(0.15), lineWidth: 14)
                    .frame(width: 130, height: 130)

                // Score ring
                Circle()
                    .trim(from: 0, to: score)
                    .stroke(ringColor(for: score), style: StrokeStyle(lineWidth: 14, lineCap: .round))
                    .frame(width: 130, height: 130)
                    .rotationEffect(.degrees(-90))
                    .animation(.easeOut(duration: 0.8), value: score)

                // Score label
                VStack(spacing: 2) {
                    Text("\(Int(score * 100))%")
                        .font(.system(size: 28, weight: .bold, design: .rounded))
                        .foregroundStyle(ringColor(for: score))
                }
            }

            Text("VoiceFlow sizi \(Int(score * 100)) oraninda dogru anlıyor")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 8)
    }

    private func ringColor(for score: Double) -> Color {
        switch score {
        case 0.8...: return .green
        case 0.6...: return .orange
        default:     return .red
        }
    }

    // MARK: - Stats Row

    private func statsRow(stats: MySpaceStats) -> some View {
        HStack(spacing: 16) {
            statCard(
                value: "\(stats.weekTranscripts)",
                label: "Bu hafta transkript",
                icon: "waveform",
                color: .blue
            )
            statCard(
                value: "\(stats.weekWords)",
                label: "Bu hafta kelime",
                icon: "text.word.spacing",
                color: .purple
            )
            statCard(
                value: "\(stats.totalTranscripts)",
                label: "Toplam transkript",
                icon: "chart.bar",
                color: .teal
            )
        }
    }

    private func statCard(value: String, label: String, icon: String, color: Color) -> some View {
        VStack(spacing: 8) {
            Image(systemName: icon)
                .font(.title3)
                .foregroundStyle(color)
            Text(value)
                .font(.system(size: 24, weight: .bold, design: .rounded))
                .foregroundStyle(color)
            Text(label)
                .font(.caption)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity)
        .padding(14)
        .background(.fill.opacity(0.4))
        .clipShape(RoundedRectangle(cornerRadius: 10))
    }

    // MARK: - Corrections Feed

    private var correctionsSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Son Duzeltmeler")
                    .font(.headline)
                Spacer()
                Button {
                    trainingSessionController.show()
                } label: {
                    Label("5 Cumle Soyle", systemImage: "mic.fill")
                        .font(.callout)
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.small)
            }

            if viewModel.mySpaceCorrections.isEmpty {
                HStack(spacing: 8) {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundStyle(.green)
                    Text("Hic duzeltme yok — harika!")
                        .font(.callout)
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(12)
                .background(.fill.opacity(0.3))
                .clipShape(RoundedRectangle(cornerRadius: 8))
            } else {
                VStack(spacing: 8) {
                    ForEach(viewModel.mySpaceCorrections.prefix(20)) { item in
                        correctionRow(item: item)
                    }
                }
            }
        }
    }

    private func correctionRow(item: CorrectionItem) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 4) {
                Image(systemName: "mic")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                Text(item.rawText)
                    .font(.callout)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
            HStack(spacing: 4) {
                Image(systemName: "arrow.right")
                    .font(.caption2)
                    .foregroundStyle(.blue)
                Text(item.text)
                    .font(.callout)
                    .fontWeight(.medium)
                    .lineLimit(1)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(10)
        .background(.fill.opacity(0.3))
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }

    // MARK: - Empty State

    private var emptyStateView: some View {
        VStack(spacing: 20) {
            Spacer()

            Image(systemName: "waveform.and.mic")
                .font(.system(size: 48))
                .foregroundStyle(.blue.opacity(0.6))

            VStack(spacing: 8) {
                Text("Henuz yeterli veri yok")
                    .font(.title3.bold())
                Text("Kullanmaya basla ve VoiceFlow sizi daha iyi tanıyacak.")
                    .font(.body)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: 380)
            }

            Button {
                trainingSessionController.show()
            } label: {
                Label("5 Cumle Soyle", systemImage: "mic.fill")
                    .frame(minWidth: 200)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)

            Spacer()
        }
        .padding(32)
    }

    // MARK: - Loading

    private var loadingView: some View {
        VStack(spacing: 16) {
            ProgressView()
            Text("Yukleniyor...")
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
