"""Quick test - 3 second recording."""

import time
import numpy as np

print("WhisperFlow Quick Test")
print("======================\n")

# Import modules
print("Loading modules...")
from whisperflow.audio import AudioCapture, AudioConfig
from whisperflow.transcription import WhisperTranscriber, WhisperConfig

# Initialize
audio = AudioCapture(config=AudioConfig())
transcriber = WhisperTranscriber(config=WhisperConfig())

# Warm up model (downloads on first run)
print("Loading model (first run downloads ~500MB)...")
start = time.time()
transcriber.transcribe(np.zeros(16000, dtype=np.float32))
print(f"Model loaded in {time.time() - start:.1f}s\n")

# Record
print("Recording for 3 seconds... SPEAK NOW!")
audio.start()
time.sleep(3)
audio_data = audio.stop()

print(f"Recorded {len(audio_data)/16000:.1f}s of audio")
print("Transcribing...\n")

# Transcribe
result = transcriber.transcribe(audio_data)

print("=" * 40)
print("RESULT:", result.text if result.text else "(no speech detected)")
print("=" * 40)

if result.text:
    import pyperclip
    pyperclip.copy(result.text)
    print("\n(Copied to clipboard)")
