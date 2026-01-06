"""FastAPI routes for WhisperFlow."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..audio import AudioCapture, AudioConfig
from ..transcription import WhisperTranscriber, WhisperConfig

router = APIRouter()

# Global instances
_audio_capture: AudioCapture | None = None
_transcriber: WhisperTranscriber | None = None


class StatusResponse(BaseModel):
    status: str
    is_recording: bool


class TranscriptionResponse(BaseModel):
    text: str
    language: str | None = None
    duration: float | None = None


class ConfigRequest(BaseModel):
    model: str | None = None
    language: str | None = None


def get_audio_capture() -> AudioCapture:
    global _audio_capture
    if _audio_capture is None:
        _audio_capture = AudioCapture(config=AudioConfig())
    return _audio_capture


def get_transcriber() -> WhisperTranscriber:
    global _transcriber
    if _transcriber is None:
        _transcriber = WhisperTranscriber(config=WhisperConfig())
    return _transcriber


@router.get("/status", response_model=StatusResponse)
async def get_status():
    """Get current recording status."""
    capture = get_audio_capture()
    return StatusResponse(
        status=capture.state.value,
        is_recording=capture.is_recording,
    )


@router.post("/start", response_model=StatusResponse)
async def start_recording():
    """Start recording audio."""
    capture = get_audio_capture()
    if capture.is_recording:
        raise HTTPException(status_code=400, detail="Already recording")
    capture.start()
    return StatusResponse(
        status=capture.state.value,
        is_recording=capture.is_recording,
    )


@router.post("/stop", response_model=TranscriptionResponse)
async def stop_recording():
    """Stop recording and transcribe."""
    capture = get_audio_capture()
    if not capture.is_recording:
        raise HTTPException(status_code=400, detail="Not recording")

    # Stop and get audio
    audio_data = capture.stop()

    if len(audio_data) == 0:
        return TranscriptionResponse(text="", duration=0)

    # Transcribe
    transcriber = get_transcriber()
    result = transcriber.transcribe(audio_data)

    return TranscriptionResponse(
        text=result.text,
        language=result.language,
        duration=result.duration,
    )


@router.get("/devices")
async def get_devices():
    """Get available audio input devices."""
    capture = get_audio_capture()
    return {"devices": capture.get_devices()}


@router.post("/config")
async def update_config(config: ConfigRequest):
    """Update transcription configuration."""
    global _transcriber

    current = get_transcriber()
    new_config = WhisperConfig(
        model_name=config.model or current.config.model_name,
        language=config.language if config.language is not None else current.config.language,
    )
    _transcriber = WhisperTranscriber(config=new_config)

    return {
        "model": _transcriber.config.model_name,
        "language": _transcriber.config.language,
    }
