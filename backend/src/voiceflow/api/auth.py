"""Authentication middleware — X-Api-Key (local/server) + JWT Bearer (server mode)."""

import logging
import os

from fastapi import Header, HTTPException, Request
from jose import JWTError

logger = logging.getLogger(__name__)

_BACKEND_MODE = os.getenv("BACKEND_MODE", "local")
_VALID_KEYS: set[str] = set(filter(None, os.getenv("API_KEYS", "").split(",")))

if _BACKEND_MODE == "server" and not _VALID_KEYS:
    logger.warning(
        "BACKEND_MODE=server but API_KEYS is not set — "
        "JWT Bearer auth will be used; X-Api-Key fallback disabled"
    )


async def verify_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    """FastAPI dependency: validates auth in server mode, no-op in local mode.

    Server mode priority:
      1. Authorization: Bearer <JWT>  → sets request.state.user_id / tenant_id
      2. X-Api-Key header             → legacy key-based auth (backward compat)
    """
    if _BACKEND_MODE != "server":
        request.state.tenant_id = "default"
        request.state.user_id = ""
        request.state.role = "superadmin"  # local mode: full access
        return

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.removeprefix("Bearer ").strip()
        try:
            from ..services.auth_service import decode_token
            payload = decode_token(token)
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid or expired JWT token")

        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Not an access token")

        user_id = payload.get("sub")
        # is_active check — only hit DB for deactivation, role comes from JWT claim
        from ..db import get_user_by_id
        user = await get_user_by_id(user_id)
        if user and not user.get("is_active", 1):
            raise HTTPException(status_code=401, detail="Account deactivated")

        request.state.user_id = user_id
        request.state.tenant_id = payload.get("tenant_id", "default")
        request.state.role = payload.get("role", "member")
        return

    # Fallback: X-Api-Key (backward compat)
    if x_api_key and _VALID_KEYS and x_api_key in _VALID_KEYS:
        # Respect X-User-ID header for backward compat
        request.state.user_id = request.headers.get("X-User-ID")
        request.state.tenant_id = "default"
        return

    raise HTTPException(status_code=401, detail="Invalid or missing credentials")
