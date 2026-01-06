"""CLI for WhisperFlow - simple terminal-based recording."""

import sys
import time

import pyperclip

from .audio import AudioCapture, AudioConfig
from .transcription import WhisperTranscriber, WhisperConfig


def main():
    """Simple CLI for recording and transcription."""
    print("WhisperFlow CLI")
    print("===============")
    print("Press ENTER to start recording, ENTER again to stop and transcribe.")
    print("Press Ctrl+C to exit.\n")

    # Initialize
    audio = AudioCapture(config=AudioConfig())
    transcriber = WhisperTranscriber(config=WhisperConfig())

    print("Loading model (first run may take a while)...")
    # Warm up model
    import numpy as np
    transcriber.transcribe(np.zeros(16000, dtype=np.float32))
    print("Model loaded!\n")

    try:
        while True:
            input("Press ENTER to start recording...")
            print("Recording... (press ENTER to stop)")

            audio.start()
            start_time = time.time()

            input()  # Wait for ENTER

            audio_data = audio.stop()
            duration = time.time() - start_time

            print(f"Recording stopped. Duration: {duration:.1f}s")
            print("Transcribing...")

            result = transcriber.transcribe(audio_data)

            print(f"\n--- Transcription ---")
            print(result.text)
            print(f"---------------------")

            if result.text:
                pyperclip.copy(result.text)
                print("(Copied to clipboard)\n")

    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)


if __name__ == "__main__":
    main()
