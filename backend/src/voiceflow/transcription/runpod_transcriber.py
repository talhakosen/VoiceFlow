"""RunPod transcription — offloads Whisper + LLM to cloud GPU.

Used when WHISPER_BACKEND=runpod. Local backend captures audio, sends to
RunPod pod/serverless endpoint, gets back transcribed+corrected text.

Optimization: direct pod mode sends raw WAV bytes via multipart upload
instead of base64 JSON — ~33% smaller payload, faster upload.
"""

import base64
import io
import logging
import os
import wave

import numpy as np

from ..core.interfaces import AbstractTranscriber, TranscriptionResult
from .whisper import WhisperConfig

logger = logging.getLogger(__name__)


class RunPodTranscriber(AbstractTranscriber):
    """Sends audio to RunPod for transcription + correction.

    Two modes:
    - Direct pod: multipart WAV upload to http://<ip>:<port>/inference
    - Serverless: base64 JSON to RunPod API /v2/{id}/runsync
    """

    def __init__(self, config: WhisperConfig | None = None):
        self.config = config or WhisperConfig()

        # Direct pod URL: RUNPOD_INFERENCE_URL=http://<ip>:8765/inference
        self._direct_url = os.getenv("RUNPOD_INFERENCE_URL", "")
        # Serverless: RUNPOD_ENDPOINT_ID + RUNPOD_API_TOKEN
        self.endpoint_id = os.getenv("RUNPOD_ENDPOINT_ID", "")
        self.api_key = os.getenv("RUNPOD_API_TOKEN", "")

        # Correction toggle — synced by RunPodPassthroughCorrector
        self._correction_enabled: bool = True

        # Cached from last RunPod response (used by RunPodPassthroughCorrector)
        self.last_corrected_text: str | None = None
        self.last_was_corrected: bool = False
        self.last_processing_detail: dict = {}

    def preload(self) -> None:
        if self._direct_url:
            logger.info("RunPod transcriber ready (direct): %s", self._direct_url)
            return
        if not self.endpoint_id:
            raise ValueError("RUNPOD_INFERENCE_URL or RUNPOD_ENDPOINT_ID required. Set in .env.")
        if not self.api_key:
            raise ValueError("RUNPOD_API_TOKEN is required. Set it in .env.")
        logger.info("RunPod transcriber ready (serverless): endpoint=%s", self.endpoint_id)

    def unload(self) -> None:
        pass

    def _encode_wav(self, audio: np.ndarray, sample_rate: int) -> bytes:
        """Encode float32 audio to 16-bit WAV bytes."""
        audio_int16 = (audio.astype(np.float32) * 32767).astype(np.int16)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_int16.tobytes())
        return buf.getvalue()

    def _call_direct(self, wav_bytes: bytes, mode: str) -> dict:
        """Direct pod: multipart upload — raw binary, no base64 overhead."""
        import httpx

        resp = httpx.post(
            self._direct_url,
            files={"audio": ("audio.wav", wav_bytes, "audio/wav")},
            data={
                "mode": mode,
                "language": self.config.language or "",
                "correction_enabled": str(self._correction_enabled).lower(),
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        return resp.json()

    def _call_serverless(self, wav_bytes: bytes, mode: str) -> dict:
        """Serverless API: base64 JSON (RunPod requirement)."""
        import httpx

        audio_b64 = base64.b64encode(wav_bytes).decode("ascii")
        resp = httpx.post(
            f"https://api.runpod.ai/v2/{self.endpoint_id}/runsync",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "input": {
                    "audio_base64": audio_b64,
                    "language": self.config.language,
                    "mode": mode,
                    "correction_enabled": self._correction_enabled,
                }
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "FAILED":
            raise RuntimeError(data.get("error", "RunPod job failed"))
        return data.get("output", {})

    def transcribe(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        mode: str = "general",
    ) -> TranscriptionResult:
        import httpx

        if len(audio) == 0:
            return TranscriptionResult(text="")

        wav_bytes = self._encode_wav(audio, sample_rate)

        try:
            if self._direct_url:
                output = self._call_direct(wav_bytes, mode)
            else:
                output = self._call_serverless(wav_bytes, mode)

            # Cache for RunPodPassthroughCorrector
            self.last_corrected_text = output.get("text", "")
            self.last_was_corrected = output.get("corrected", False)
            self.last_processing_detail = {
                "whisper_ms": output.get("whisper_ms", 0),
                "llm_ms": output.get("llm_ms", 0),
                "runpod_total_ms": output.get("processing_ms", 0),
            }

            raw_text = output.get("raw_text", output.get("text", ""))
            logger.info(
                "RunPod: raw='%s' corrected='%s' (whisper=%dms, llm=%dms)",
                raw_text[:60],
                self.last_corrected_text[:60] if self.last_corrected_text else "",
                output.get("whisper_ms", 0),
                output.get("llm_ms", 0),
            )

            return TranscriptionResult(
                text=raw_text,
                language=output.get("language"),
                duration=output.get("duration"),
            )

        except httpx.TimeoutException:
            logger.error("RunPod request timed out (60s)")
            return TranscriptionResult(text="")
        except Exception as e:
            logger.error("RunPod transcription failed: %s", e, exc_info=True)
            return TranscriptionResult(text="")
