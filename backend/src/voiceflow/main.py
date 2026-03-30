"""Main FastAPI application for WhisperFlow."""

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

_BACKEND_MODE = os.getenv("BACKEND_MODE", "local")
_HOST = "0.0.0.0" if _BACKEND_MODE == "server" else "127.0.0.1"

from .api import router
from .api.routes import get_transcriber, get_corrector, _mlx_executor

logger = logging.getLogger(__name__)

# Track model loading state
_model_loading = False
_model_loaded = False


async def _preload_model_background():
    """Load models in dedicated MLX thread."""
    global _model_loading, _model_loaded
    _model_loading = True
    loop = asyncio.get_running_loop()

    # Load Whisper model first
    logger.info("Preloading Whisper model in background...")
    try:
        transcriber = get_transcriber()
        await loop.run_in_executor(_mlx_executor, transcriber._ensure_model_loaded)
        _model_loaded = True
        logger.info("Whisper model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load Whisper model: {e}")

    # Then load LLM model only if correction is enabled
    corrector = get_corrector()
    if corrector.config.enabled:
        logger.info("Preloading LLM correction model in background...")
        try:
            # Ollama: HTTP pre-warm (IO-bound, no GPU executor needed)
            # MLX: GPU load (requires single MLX executor)
            if hasattr(corrector, "correct_async"):
                await loop.run_in_executor(None, corrector._ensure_model_loaded)
            else:
                await loop.run_in_executor(_mlx_executor, corrector._ensure_model_loaded)
            logger.info("LLM correction model loaded successfully")
        except Exception as e:
            logger.error("Failed to load LLM model: %s", e)
    else:
        logger.info("LLM correction disabled, skipping model preload (~4GB saved)")

    _model_loading = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start model preloading in background."""
    # Start loading in background - don't block server startup
    asyncio.create_task(_preload_model_background())
    yield


app = FastAPI(
    title="WhisperFlow",
    description="Real-time speech-to-text for macOS",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "WhisperFlow API", "version": "0.1.0"}


@app.get("/health")
async def health():
    corrector = get_corrector()
    return {
        "status": "healthy",
        "model_loaded": _model_loaded,
        "model_loading": _model_loading,
        "llm_loaded": getattr(corrector, "_model", None) is not None,
    }


def main():
    """Run the FastAPI server."""
    import uvicorn
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logger.info("Starting VoiceFlow in %s mode on %s:8765", _BACKEND_MODE.upper(), _HOST)
    uvicorn.run(app, host=_HOST, port=8765)


if __name__ == "__main__":
    main()
