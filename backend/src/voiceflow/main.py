"""Main FastAPI application for WhisperFlow."""

from fastapi import FastAPI
from .api import router

app = FastAPI(
    title="WhisperFlow",
    description="Real-time speech-to-text for macOS",
    version="0.1.0",
)

app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "WhisperFlow API", "version": "0.1.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


def main():
    """Run the FastAPI server."""
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765)


if __name__ == "__main__":
    main()
