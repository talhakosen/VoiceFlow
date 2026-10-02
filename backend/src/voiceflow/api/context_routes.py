"""Project terms routes — /context/* endpoints (smart dictionary from a code folder)."""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from .auth import verify_api_key

logger = logging.getLogger(__name__)

context_router = APIRouter(dependencies=[Depends(verify_api_key)])


def _user_id(request: Request, x_user_id: str | None) -> str:
    return x_user_id or getattr(request.state, "user_id", None) or "default"


def _last_index_paths(request: Request) -> dict:
    if not hasattr(request.app.state, "last_index_paths"):
        request.app.state.last_index_paths = {}
    return request.app.state.last_index_paths


class IngestRequest(BaseModel):
    path: str


@context_router.post("/context/ingest")
async def context_ingest(
    body: IngestRequest,
    request: Request,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    """Scan folder, extract identifiers, populate smart dictionary."""
    from ..services.context_service import start_ingest
    try:
        result = await start_ingest(
            path=body.path,
            user_id=_user_id(request, x_user_id),
            last_index_paths=_last_index_paths(request),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    request.app.state.ingest_task = None  # reset; actual task is fire-and-forget
    return result


@context_router.get("/context/status")
async def context_status(
    request: Request,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    """Return smart dictionary status."""
    from ..services.context_service import get_status
    return await get_status(
        user_id=_user_id(request, x_user_id),
        last_index_paths=_last_index_paths(request),
    )


@context_router.delete("/context")
async def context_clear(
    request: Request,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    """Clear smart dictionary entries for this user."""
    from ..services.context_service import wipe_context
    return await wipe_context(user_id=_user_id(request, x_user_id))
