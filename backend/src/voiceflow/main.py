"""Main FastAPI application for VoiceFlow."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from .api import router, engineering_router
from .api.auth_routes import router as auth_router
from .api.admin_routes import router as admin_router
from .core.config import BACKEND_MODE as _BACKEND_MODE, LLM_BACKEND, LLM_ENDPOINT
from .db import init_db

_HOST = "0.0.0.0" if _BACKEND_MODE == "server" else "127.0.0.1"

logger = logging.getLogger(__name__)


def _build_transcriber():
    if _BACKEND_MODE == "server":
        from .transcription.faster_whisper import FasterWhisperTranscriber
        from .transcription import WhisperConfig
        return FasterWhisperTranscriber(config=WhisperConfig())
    from .transcription import WhisperTranscriber, WhisperConfig
    return WhisperTranscriber(config=WhisperConfig())


def _build_corrector():
    use_ollama = (
        LLM_BACKEND == "ollama"
        or _BACKEND_MODE == "server"
        or bool(LLM_ENDPOINT)
    )
    if use_ollama:
        from .correction.ollama_corrector import OllamaCorrector, OllamaCorrectorConfig
        logger.info("Using OllamaCorrector (endpoint: %s)", LLM_ENDPOINT or "http://localhost:11434")
        return OllamaCorrector(config=OllamaCorrectorConfig())
    from .correction import LLMCorrector, CorrectorConfig
    logger.info("Using MLX LLMCorrector")
    return LLMCorrector(config=CorrectorConfig())


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    from .services import RecordingService
    service = RecordingService(
        transcriber=_build_transcriber(),
        corrector=_build_corrector(),
    )
    app.state.recording_service = service

    asyncio.create_task(service.preload_models())
    yield


app = FastAPI(
    title="VoiceFlow",
    description="Real-time speech-to-text for macOS",
    version="0.2.0",
    lifespan=lifespan,
)

# Jinja2 templates — backend/templates/
# __file__ = backend/src/voiceflow/main.py → .parent.parent.parent = backend/
import pathlib as _pathlib
_templates_dir = _pathlib.Path(__file__).parent.parent.parent / "templates"
app.state.templates = Jinja2Templates(directory=str(_templates_dir))

app.include_router(router, prefix="/api")
app.include_router(engineering_router, prefix="/api")
app.include_router(auth_router, prefix="/auth")
app.include_router(admin_router)


@app.get("/")
async def root():
    return {"message": "VoiceFlow API", "version": "0.2.0"}


@app.get("/health")
async def health(request: Request):
    svc = request.app.state.recording_service
    corrector = svc.corrector
    return {
        "status": "healthy",
        "model_loaded": getattr(svc.transcriber, "_model", None) is not None,
        "llm_loaded": getattr(corrector, "_model", None) is not None,
    }


def main():
    import uvicorn
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logger.info("Starting VoiceFlow in %s mode on %s:8765", _BACKEND_MODE.upper(), _HOST)
    uvicorn.run(app, host=_HOST, port=8765)


if __name__ == "__main__":
    main()
