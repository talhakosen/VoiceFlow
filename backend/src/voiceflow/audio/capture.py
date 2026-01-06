"""Audio capture module using sounddevice."""

import queue
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

import numpy as np
import sounddevice as sd


class RecordingState(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    STOPPED = "stopped"


@dataclass
class AudioConfig:
    """Audio capture configuration."""

    sample_rate: int = 16000  # Whisper expects 16kHz
    channels: int = 1
    dtype: str = "float32"
    blocksize: int = 1024


@dataclass
class AudioCapture:
    """Captures audio from microphone."""

    config: AudioConfig = field(default_factory=AudioConfig)
    _state: RecordingState = field(default=RecordingState.IDLE, init=False)
    _audio_queue: queue.Queue = field(default_factory=queue.Queue, init=False)
    _recorded_chunks: list = field(default_factory=list, init=False)
    _stream: sd.InputStream | None = field(default=None, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    @property
    def state(self) -> RecordingState:
        return self._state

    @property
    def is_recording(self) -> bool:
        return self._state == RecordingState.RECORDING

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: dict,
        status: sd.CallbackFlags
    ) -> None:
        """Callback for audio stream."""
        if status:
            print(f"Audio callback status: {status}")
        if self._state == RecordingState.RECORDING:
            self._audio_queue.put(indata.copy())

    def start(self) -> None:
        """Start recording audio."""
        with self._lock:
            if self._state == RecordingState.RECORDING:
                return

            self._recorded_chunks = []
            while not self._audio_queue.empty():
                self._audio_queue.get()

            self._stream = sd.InputStream(
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                dtype=self.config.dtype,
                blocksize=self.config.blocksize,
                callback=self._audio_callback,
            )
            self._stream.start()
            self._state = RecordingState.RECORDING

    def stop(self) -> np.ndarray:
        """Stop recording and return audio data."""
        with self._lock:
            if self._state != RecordingState.RECORDING:
                return np.array([], dtype=np.float32)

            self._state = RecordingState.STOPPED

            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None

            # Collect all queued audio
            while not self._audio_queue.empty():
                self._recorded_chunks.append(self._audio_queue.get())

            if not self._recorded_chunks:
                return np.array([], dtype=np.float32)

            # Concatenate all chunks
            audio_data = np.concatenate(self._recorded_chunks, axis=0)
            # Flatten to 1D if needed
            if audio_data.ndim > 1:
                audio_data = audio_data.flatten()

            self._state = RecordingState.IDLE
            return audio_data

    def get_devices(self) -> list[dict]:
        """Get list of available input devices."""
        devices = sd.query_devices()
        input_devices = []
        for i, device in enumerate(devices):
            if device["max_input_channels"] > 0:
                input_devices.append({
                    "id": i,
                    "name": device["name"],
                    "channels": device["max_input_channels"],
                    "sample_rate": device["default_samplerate"],
                })
        return input_devices

    def __del__(self):
        """Cleanup on deletion."""
        if self._stream:
            self._stream.stop()
            self._stream.close()
