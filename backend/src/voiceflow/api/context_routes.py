"""Context Engine routes — /context/* and /symbol/* endpoints."""

import asyncio
import logging
from pathlib import Path

import aiosqlite
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from .auth import verify_api_key
from ..db.storage import DB_PATH as _db_path

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
    user_id = x_user_id or getattr(request.state, "user_id", None) or "default"
    async with aiosqlite.connect(_db_path) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM user_dictionary WHERE user_id = ? AND scope = 'smart'",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            n = row[0] if row else 0
        async with db.execute(
            "SELECT COUNT(*), MAX(indexed_at) FROM symbol_index_v2 WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            row2 = await cursor.fetchone()
            sym_count = row2[0] if row2 else 0
            last_indexed_at = row2[1] if row2 else None

    last_paths = getattr(request.app.state, "last_index_paths", {}) if request else {}
    entry = last_paths.get(user_id) or last_paths.get("default")
    return {
        "count": n,
        "is_ready": True,
        "is_empty": n == 0,
        "symbol_count": sym_count,
        "last_indexed_at": last_indexed_at,
        "last_index_path": entry["path"] if entry else None,
    }


@context_router.get("/context/projects")
async def context_projects(
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    request: Request = None,
):
    """Return indexed projects with smart dictionary + symbol counts."""
    user_id = x_user_id or getattr(request.state, "user_id", None) or "default"
    async with aiosqlite.connect(_db_path) as db:
        async with db.execute(
            "SELECT project_path, COUNT(*) FROM symbol_index WHERE user_id = ? GROUP BY project_path",
            (user_id,),
        ) as cursor:
            symbol_rows = {row[0]: row[1] for row in await cursor.fetchall()}

        async with db.execute(
            "SELECT COUNT(*) FROM user_dictionary WHERE user_id = ? AND scope = 'smart'",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            smart_total = row[0] if row else 0

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
    user_id = x_user_id or getattr(request.state, "user_id", None) or "default"
    async with aiosqlite.connect(_db_path) as db:
        await db.execute("DELETE FROM user_dictionary WHERE user_id = ?", (user_id,))
        await db.commit()
    return {"status": "cleared"}
