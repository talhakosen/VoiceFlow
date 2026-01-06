# VoiceFlow

Real-time speech-to-text for macOS using Apple Silicon optimized Whisper.

**100% Local** - No data leaves your Mac. Privacy-friendly.

## Features

- **Push-to-talk**: Double-tap Fn, hold and speak, release to transcribe
- **Auto-paste**: Transcribed text automatically pasted to active app
- **Turkish + English**: Works with mixed language (code-switching)
- **Menu bar app**: Minimal, always accessible
- **Fast**: Optimized for Apple Silicon (M1/M2/M3/M4)

## Requirements

- macOS 13.0+
- Apple Silicon Mac (M1/M2/M3/M4)
- Python 3.11+
- Xcode 15+ (for building the app)

## Installation

### 1. Clone and setup backend

```bash
git clone https://github.com/talhakosen/VoiceFlow.git
cd VoiceFlow
./scripts/setup.sh
```

### 2. Download the model (first time only, ~500MB)

```bash
cd backend && source .venv/bin/activate
python -c "import mlx_whisper; mlx_whisper.transcribe('test', path_or_hf_repo='mlx-community/whisper-small-mlx')"
```

### 3. Build the macOS app

```bash
# Install xcodegen if needed
brew install xcodegen

# Generate and build
cd VoiceFlowApp
xcodegen generate
xcodebuild -scheme VoiceFlowApp -configuration Release build

# Copy to Applications
cp -R ~/Library/Developer/Xcode/DerivedData/VoiceFlowApp-*/Build/Products/Release/VoiceFlow.app /Applications/
```

### 4. Grant permissions

On first launch, grant these permissions:
- **Accessibility**: For global hotkey (Fn key)
- **Microphone**: For audio recording
- **Automation**: For auto-paste

## Usage

1. Launch VoiceFlow from Applications
2. Look for the waveform icon in the menu bar
3. **Double-tap Fn** to activate push-to-talk
4. **Hold Fn** and speak
5. **Release Fn** - text is transcribed and pasted

## Architecture

```
┌─────────────────────────────────────┐
│     VoiceFlow.app (SwiftUI)         │
│  • Menu bar icon                    │
│  • Global hotkey (Fn)               │
│  • Auto-paste                       │
└──────────────┬──────────────────────┘
               │ HTTP (localhost:8765)
┌──────────────▼──────────────────────┐
│     Python Backend (FastAPI)        │
│  • Audio capture (sounddevice)      │
│  • Transcription (mlx-whisper)      │
└─────────────────────────────────────┘
```

## Privacy

- **100% Local**: All processing happens on your Mac
- **No cloud**: No data sent to external servers
- **Offline**: Works without internet (after model download)

## License

MIT License - See [LICENSE](LICENSE) for details.

## Acknowledgments

- [mlx-whisper](https://github.com/ml-explore/mlx-examples) - Apple Silicon optimized Whisper
- [OpenAI Whisper](https://github.com/openai/whisper) - Original speech recognition model
