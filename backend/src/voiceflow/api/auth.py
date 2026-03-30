"""API key authentication — active only in server mode."""

import logging
import os

from fastapi import Header, HTTPException

logger = logging.getLogger(__name__)

_BACKEND_MODE = os.getenv("BACKEND_MODE", "local")
_VALID_KEYS: set[str] = set(filter(None, os.getenv("API_KEYS", "").split(",")))

if _BACKEND_MODE == "server" and not _VALID_KEYS:
    logger.warning("BACKEND_MODE=server but API_KEYS is not set — all requests will be rejected")


async def verify_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    """FastAPI dependency: validates API key in server mode, no-op in local mode."""
    if _BACKEND_MODE != "server":
        return
    if not x_api_key or x_api_key not in _VALID_KEYS:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
