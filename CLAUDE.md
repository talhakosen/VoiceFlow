# VoiceFlow

Real-time speech-to-text for macOS using mlx-whisper + mlx-lm.

## Quick Start

```bash
./voiceflow.sh start    # Start backend
./voiceflow.sh stop     # Stop backend
./voiceflow.sh restart  # Restart backend
./voiceflow.sh status   # Check status
```

### macOS App Build & Deploy
```bash
pkill -f "VoiceFlow.app" 2>/dev/null
rm -rf ~/Library/Developer/Xcode/DerivedData/VoiceFlowApp-*
xcodebuild -project VoiceFlowApp/VoiceFlowApp.xcodeproj -scheme VoiceFlowApp -configuration Debug clean build
rm -rf /Applications/VoiceFlow.app
cp -R ~/Library/Developer/Xcode/DerivedData/VoiceFlowApp-*/Build/Products/Debug/VoiceFlow.app /Applications/
open /Applications/VoiceFlow.app
```

## Usage

- Double-tap Fn → start recording
- Double-tap Fn again OR release Fn → stop recording & transcribe
- Menu bar: Force Stop (Cmd+S) if stuck
- Smart Correction: menu toggle, Turkish text auto-correction via LLM

## Architecture

- `backend/src/voiceflow/` - Python backend (FastAPI, port 8765)
- `backend/src/voiceflow/transcription/` - mlx-whisper module
- `backend/src/voiceflow/correction/` - LLM correction module (mlx-lm)
- `backend/src/voiceflow/audio/` - Audio capture (sounddevice)
- `VoiceFlowApp/` - Swift menu bar app

## API

- `POST /api/start` - Start recording
- `POST /api/stop` - Stop & transcribe (+ optional LLM correction)
- `GET /api/status` - Recording status
- `POST /api/config` - Config (language, task, correction_enabled)
- `GET /health` - Health check (model_loaded, llm_loaded)

## Key Config

- Whisper: `mlx-community/whisper-small-mlx`
- LLM correction: `mlx-community/Qwen2.5-7B-Instruct-4bit` (~4GB)
- Python venv: `backend/.venv` (python3.14)
- MLX executor: single-thread (Metal GPU not thread-safe)

## Dev Notes

- venv path: `backend/.venv/bin/python` - recreate with `python3 -m venv .venv` if broken
- HF_TOKEN in env speeds up model downloads (unauthenticated = very slow)
- Fn key release events unreliable on macOS → double-tap toggle + Force Stop as fallbacks
- Small LLMs (1.5B, 3B) hallucinate on Turkish correction → 7B minimum for quality
- LLM prompt uses few-shot examples + greedy decoding (temp=0) for deterministic output
- After Swift changes: always clean build + copy to /Applications
