"""Audio capture module using sounddevice."""

import logging
import queue
import threading
from dataclasses import dataclass, field
from enum import Enum

import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)


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
    _recorded_chunks: list[np.ndarray] = field(default_factory=list, init=False)
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
        frames: int,  # noqa: ARG002
        time_info: dict,  # noqa: ARG002
        status: sd.CallbackFlags,
    ) -> None:
        """Callback for audio stream — runs in sounddevice thread."""
        if status:
            logger.warning("Audio callback status: %s", status)
        if self._state == RecordingState.RECORDING:
            self._audio_queue.put(indata.copy())

    def start(self) -> None:
        """Start recording audio."""
        with self._lock:
            if self._state == RecordingState.RECORDING:
                return

            self._recorded_chunks = []
            while not self._audio_queue.empty():
                self._audio_queue.get_nowait()

            self._stream = sd.InputStream(
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                dtype=self.config.dtype,
                blocksize=self.config.blocksize,
                callback=self._audio_callback,
            )
            self._stream.start()
            self._state = RecordingState.RECORDING
            logger.debug("Audio capture started")

    def stop(self) -> np.ndarray:
        """Stop recording and return audio data as float32 mono array."""
        with self._lock:
            if self._state != RecordingState.RECORDING:
                return np.array([], dtype=np.float32)

            # Stop stream FIRST while state is still RECORDING so the
            # callback flushes remaining buffered audio into the queue.
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None

            self._state = RecordingState.STOPPED

            # Drain queue non-blocking — no busy-wait needed after stream.stop()
            while True:
                try:
                    self._recorded_chunks.append(self._audio_queue.get_nowait())
                except queue.Empty:
                    break

            if not self._recorded_chunks:
                self._state = RecordingState.IDLE
                return np.array([], dtype=np.float32)

            audio_data = np.concatenate(self._recorded_chunks, axis=0)
            if audio_data.ndim > 1:
                audio_data = audio_data.flatten()

            self._recorded_chunks = []
            self._state = RecordingState.IDLE
            logger.debug("Audio capture stopped: %.2fs", len(audio_data) / self.config.sample_rate)
            return audio_data

    def force_reset(self) -> None:
        """Force-reset state and close stream (safe to call from any state)."""
        with self._lock:
            if self._stream is not None:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None
            self._recorded_chunks = []
            self._state = RecordingState.IDLE
            logger.debug("Audio capture force-reset")

    def get_devices(self) -> list[dict]:
        """Return available audio input devices."""
        devices = sd.query_devices()
        return [
            {
                "id": i,
                "name": device["name"],
                "channels": device["max_input_channels"],
                "sample_rate": device["default_samplerate"],
            }
            for i, device in enumerate(devices)
            if device["max_input_channels"] > 0
        ]

    def __del__(self) -> None:
        """Best-effort cleanup on GC — swallow all errors."""
        try:
            stream = getattr(self, "_stream", None)
            if stream is not None:
                stream.stop()
                stream.close()
        except Exception:
            pass
