# VoiceFlow

Real-time speech-to-text for macOS using mlx-whisper.

## Quick Start

```bash
# Backend
cd backend
source .venv/bin/activate
python -m voiceflow.cli  # Terminal mode
# or
python -m voiceflow.main  # API server (port 8765)

# App
open VoiceFlowApp/VoiceFlowApp.xcodeproj
# Build & Run (Cmd+R)
```

## Usage

1. Double-tap Fn key (push-to-talk mode)
2. Hold Fn and speak
3. Release Fn → text is transcribed and auto-pasted

## Architecture

- `backend/src/voiceflow/` - Python backend (mlx-whisper)
- `VoiceFlowApp/` - SwiftUI menu bar app

## API Endpoints

- `POST /api/start` - Start recording
- `POST /api/stop` - Stop & transcribe
- `GET /api/status` - Recording status

## Config

Default model: `mlx-community/whisper-small-mlx` (Turkish)
