"""Context Engine routes — /context/* and /symbol/* endpoints."""

import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from .auth import verify_api_key

logger = logging.getLogger(__name__)

context_router = APIRouter(dependencies=[Depends(verify_api_key)])


def _validate_ingest_path(raw_path: str) -> Path:
    """Resolve and validate a user-supplied path for context ingest.

    Raises HTTPException 400 if the path doesn't exist or is not a directory.
    """
    try:
        resolved = Path(raw_path).resolve()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid path")
    if not resolved.exists():
        raise HTTPException(status_code=400, detail=f"Path does not exist: {raw_path}")
    if not resolved.is_dir():
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {raw_path}")
    return resolved


class IngestRequest(BaseModel):
    path: str


@context_router.post("/context/ingest")
async def context_ingest(
    body: IngestRequest,
    request: Request,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    """Scan folder, extract identifiers, populate smart dictionary."""
    from ..services.smart_dictionary import build_smart_dictionary

    validated_path = _validate_ingest_path(body.path)
    user_id = x_user_id or getattr(request.state, "user_id", None) or "default"

    async def _run():
        path_str = str(validated_path)
        try:
            added = await build_smart_dictionary(path_str, user_id)
            logger.info("Smart dictionary: %d entries added for user %s", added, user_id)
        except Exception as e:
            logger.warning("Smart dictionary failed: %s", e)
        try:
            from ..symbol import build_symbol_index, generate_project_notes
            sym_count = await build_symbol_index(path_str, user_id)
            logger.info("Symbol index: %d symbols for user %s", sym_count, user_id)
            if sym_count > 0:
                notes_path = await generate_project_notes(path_str, user_id)
                if notes_path:
                    logger.info("Project notes generated: %s", notes_path)
        except Exception as e:
            logger.warning("Symbol index failed: %s", e)

    import time as _t
    if not hasattr(request.app.state, "last_index_paths"):
        request.app.state.last_index_paths = {}
    request.app.state.last_index_paths[user_id] = {"path": str(validated_path), "indexed_at": _t.time()}

    task = asyncio.create_task(_run())
    request.app.state.ingest_task = task
    return {"status": "started", "path": str(validated_path), "message": "Smart dictionary scan in background"}


@context_router.get("/context/status")
async def context_status(
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    request: Request = None,
):
    """Return smart dictionary + symbol index status."""
    from ..db.storage import get_context_status as _get_context_status
    user_id = x_user_id or getattr(request.state, "user_id", None) or "default"
    stats = await _get_context_status(user_id)
    last_paths = getattr(request.app.state, "last_index_paths", {}) if request else {}
    entry = last_paths.get(user_id) or last_paths.get("default")
    return {
        "count": stats["smart_count"],
        "is_ready": True,
        "is_empty": stats["smart_count"] == 0,
        "symbol_count": stats["symbol_count"],
        "last_indexed_at": stats["last_indexed_at"],
        "last_index_path": entry["path"] if entry else None,
    }


@context_router.get("/context/projects")
async def context_projects(
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    request: Request = None,
):
    """Return indexed projects with smart dictionary + symbol counts."""
    from ..db.storage import get_context_projects as _get_context_projects
    user_id = x_user_id or getattr(request.state, "user_id", None) or "default"
    data = await _get_context_projects(user_id)
    symbol_rows = data["symbol_rows"]
    smart_total = data["smart_total"]
    projects = [
        {"path": path, "name": Path(path).name, "symbol_count": sym_count}
        for path, sym_count in symbol_rows.items()
    ]
    return {
        "projects": projects,
        "smart_word_count": smart_total,
        "total_symbols": sum(p["symbol_count"] for p in projects),
    }


@context_router.get("/symbol/lookup")
async def symbol_lookup(
    q: str,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    request: Request = None,
    limit: int = 5,
):
    """Fuzzy symbol lookup. Returns file_path:line_number matches."""
    from ..symbol import lookup_symbol
    user_id = x_user_id or getattr(request.state, "user_id", None) or "default"
    results = await lookup_symbol(query=q, user_id=user_id, limit=limit)
    return {"query": q, "results": results}


@context_router.delete("/context")
async def context_clear(
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    request: Request = None,
):
    """Clear smart dictionary entries for this user."""
    from ..db.storage import clear_smart_dictionary
    user_id = x_user_id or getattr(request.state, "user_id", None) or "default"
    await clear_smart_dictionary(user_id=user_id)
    return {"status": "cleared"}
