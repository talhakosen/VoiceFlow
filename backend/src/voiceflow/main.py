"""Main FastAPI application for VoiceFlow."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .api import router, engineering_router, context_router, training_router
from .api.auth_routes import router as auth_router
from .api.admin_routes import router as admin_router
from .core.config import (
    BACKEND_MODE as _BACKEND_MODE,
    LLM_BACKEND, LLM_ENDPOINT,
    WHISPER_MODEL as _WHISPER_MODEL,
    WHISPER_IT_MODEL as _WHISPER_IT_MODEL,
    WHISPER_BACKEND as _WHISPER_BACKEND,
    CORS_ORIGINS,
)
from .core.logging import setup_logging
from .core.rate_limit import limiter
from .db import init_db

_HOST = "0.0.0.0" if _BACKEND_MODE == "server" else "127.0.0.1"

logger = logging.getLogger(__name__)



def _build_transcriber():
    if _WHISPER_BACKEND == "runpod":
        from .transcription.runpod_transcriber import RunPodTranscriber
        from .transcription import WhisperConfig
        logger.info("Using RunPod serverless transcriber")
        return RunPodTranscriber(config=WhisperConfig())
    if _BACKEND_MODE == "server":
        from .transcription.faster_whisper import FasterWhisperTranscriber
        from .transcription import WhisperConfig
        return FasterWhisperTranscriber(config=WhisperConfig())
    from .transcription import WhisperTranscriber, WhisperConfig
    return WhisperTranscriber(config=WhisperConfig(it_model_name=_WHISPER_IT_MODEL or None))


def _build_corrector():
    if _WHISPER_BACKEND == "runpod":
        # RunPod serverless handler does correction internally — use a no-op corrector
        from .correction.runpod_passthrough import RunPodPassthroughCorrector
        logger.info("Using RunPodPassthroughCorrector (correction handled on RunPod)")
        return RunPodPassthroughCorrector()
    use_ollama = (
        LLM_BACKEND == "ollama"
        or _BACKEND_MODE == "server"
        or bool(LLM_ENDPOINT)
    )
    if use_ollama:
        from .correction import APICorrector, APICorrectorConfig
        logger.info("Using APICorrector (endpoint: %s)", LLM_ENDPOINT or "http://localhost:11434")
        return APICorrector(config=APICorrectorConfig())
    from .correction import MLXCorrector, MLXCorrectorConfig
    logger.info("Using MLXCorrector (local, Metal GPU)")
    return MLXCorrector(config=MLXCorrectorConfig())


async def _purge_tokens_loop() -> None:
    """Purge expired JWT blacklist entries once per hour."""
    from .db import purge_expired_tokens
    while True:
        await asyncio.sleep(3600)
        try:
            removed = await purge_expired_tokens()
            if removed:
                logger.info("JWT blacklist: purged %d expired token(s)", removed)
        except Exception:
            pass


async def _autoload_bundle() -> None:
    """Load IT bundle into DB on startup if DB count differs from file (covers first run + updates)."""
    import json, pathlib
    from .db.dictionary_storage import count_bundle_entries, load_bundle_entries

    bundle_path = pathlib.Path(__file__).parent.parent.parent.parent / "ml" / "dictionary" / "it_bundle_full.json"
    if not bundle_path.exists():
        logger.warning("IT bundle not found at %s — skipping auto-load", bundle_path)
        return

    try:
        with open(bundle_path, encoding="utf-8") as f:
            entries = json.load(f)
    except Exception as exc:
        logger.warning("IT bundle read failed: %s", exc)
        return

    db_count = await count_bundle_entries("default")
    if db_count == len(entries):
        logger.info("IT bundle up-to-date (%d entries) — skipping", db_count)
        return

    loaded = await load_bundle_entries("default", entries)
    logger.info("IT bundle auto-loaded: %d entries (was %d)", loaded, db_count)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    from .services import RecordingService
    transcriber = _build_transcriber()
    corrector = _build_corrector()

    # RunPod mode: link corrector to transcriber for cached results
    if _WHISPER_BACKEND == "runpod" and hasattr(corrector, "set_transcriber"):
        corrector.set_transcriber(transcriber)

    service = RecordingService(
        transcriber=transcriber,
        corrector=corrector,
    )
    app.state.recording_service = service

    asyncio.create_task(service.preload_models())
    asyncio.create_task(_purge_tokens_loop())
    asyncio.create_task(_autoload_bundle())
    yield


app = FastAPI(
    title="VoiceFlow",
    description="Real-time speech-to-text for macOS",
    version="0.2.0",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

# Jinja2 templates — backend/templates/
# __file__ = backend/src/voiceflow/main.py → .parent.parent.parent = backend/
import pathlib as _pathlib  # noqa: E402
_templates_dir = _pathlib.Path(__file__).parent.parent.parent / "templates"
app.state.templates = Jinja2Templates(directory=str(_templates_dir))

app.include_router(router, prefix="/api")
app.include_router(engineering_router, prefix="/api")
app.include_router(context_router, prefix="/api")
app.include_router(training_router, prefix="/api")
app.include_router(auth_router, prefix="/auth")
app.include_router(admin_router)


@app.get("/")
async def root():
    return {"message": "VoiceFlow API", "version": "0.2.0"}


@app.get("/health")
async def health(request: Request):
    svc = request.app.state.recording_service
    corrector = svc.corrector
    import os
    model_display = os.path.basename(_WHISPER_MODEL.rstrip("/"))
    from .core.config import LLM_ADAPTER_VERSION
    adapter_version = f"v{LLM_ADAPTER_VERSION}" if LLM_ADAPTER_VERSION else None
    return {
        "status": "healthy",
        "model_loaded": getattr(svc.transcriber, "_model_loaded", False) or getattr(svc.transcriber, "_model", None) is not None,
        "llm_loaded": getattr(corrector, "_model", None) is not None,
        "whisper_model": model_display,
        "adapter_version": adapter_version,
    }


def main():
    import uvicorn
    setup_logging()
    logger.info("Starting VoiceFlow in %s mode on %s:8765", _BACKEND_MODE.upper(), _HOST)
    uvicorn.run(app, host=_HOST, port=8765)


if __name__ == "__main__":
    main()
