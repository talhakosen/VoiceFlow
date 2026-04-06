"""ContextService — smart dictionary + symbol index business logic."""

import asyncio
import logging
import time
from pathlib import Path

from ..db import get_context_status, get_context_projects, clear_smart_dictionary

logger = logging.getLogger(__name__)


def validate_ingest_path(raw_path: str) -> Path:
    """Resolve and validate a user-supplied folder path.

    Raises ValueError if path is invalid, missing, or not a directory.
    """
    try:
        resolved = Path(raw_path).resolve()
    except Exception:
        raise ValueError("Invalid path")
    if not resolved.exists():
        raise ValueError(f"Path does not exist: {raw_path}")
    if not resolved.is_dir():
        raise ValueError(f"Path is not a directory: {raw_path}")
    return resolved


async def start_ingest(
    path: str,
    user_id: str,
    last_index_paths: dict,
) -> dict:
    """Validate path and kick off background ingest. Returns status dict.

    `last_index_paths` is app.state.last_index_paths — mutated in place.
    Raises ValueError on bad path.
    """
    resolved = validate_ingest_path(path)
    path_str = str(resolved)

    if not isinstance(last_index_paths, dict):
        last_index_paths.clear()

    last_index_paths[user_id] = {"path": path_str, "indexed_at": time.time()}

    async def _run() -> None:
        try:
            from ..services.smart_dictionary import build_smart_dictionary
            added = await build_smart_dictionary(path_str, user_id)
            logger.info("Smart dictionary: %d entries added for user %s", added, user_id)
        except Exception as exc:
            logger.warning("Smart dictionary failed: %s", exc)
        try:
            from ..symbol import build_symbol_index, generate_project_notes
            sym_count = await build_symbol_index(path_str, user_id)
            logger.info("Symbol index: %d symbols for user %s", sym_count, user_id)
            if sym_count > 0:
                notes_path = await generate_project_notes(path_str, user_id)
                if notes_path:
                    logger.info("Project notes generated: %s", notes_path)
        except Exception as exc:
            logger.warning("Symbol index failed: %s", exc)

    asyncio.create_task(_run())
    return {"status": "started", "path": path_str, "message": "Smart dictionary scan in background"}


async def get_status(user_id: str, last_index_paths: dict) -> dict:
    """Return smart dictionary + symbol index status for a user."""
    stats = await get_context_status(user_id)
    entry = last_index_paths.get(user_id) or last_index_paths.get("default")
    return {
        "count": stats["smart_count"],
        "is_ready": True,
        "is_empty": stats["smart_count"] == 0,
        "symbol_count": stats["symbol_count"],
        "last_indexed_at": stats["last_indexed_at"],
        "last_index_path": entry["path"] if entry else None,
    }


async def get_projects(user_id: str) -> dict:
    """Return indexed projects with smart dictionary + symbol counts."""
    data = await get_context_projects(user_id)
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


async def wipe_context(user_id: str) -> dict:
    """Clear smart dictionary entries for a user."""
    await clear_smart_dictionary(user_id=user_id)
    return {"status": "cleared"}
