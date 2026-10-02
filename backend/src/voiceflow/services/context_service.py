"""ContextService — project terms (smart dictionary) business logic."""

import asyncio
import logging
import time
from pathlib import Path

from ..db import get_context_status, clear_smart_dictionary

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
            from ..indexing.smart_dictionary import build_smart_dictionary
            added = await build_smart_dictionary(path_str, user_id)
            logger.info("Smart dictionary: %d entries added for user %s", added, user_id)
        except Exception as exc:
            logger.warning("Smart dictionary failed: %s", exc)
    asyncio.create_task(_run())
    return {"status": "started", "path": path_str, "message": "Smart dictionary scan in background"}


async def get_status(user_id: str, last_index_paths: dict) -> dict:
    """Return smart dictionary status for a user."""
    stats = await get_context_status(user_id)
    entry = last_index_paths.get(user_id) or last_index_paths.get("default")
    return {
        "count": stats["smart_count"],
        "is_ready": True,
        "is_empty": stats["smart_count"] == 0,
        "last_index_path": entry["path"] if entry else None,
    }


async def wipe_context(user_id: str) -> dict:
    """Clear smart dictionary entries for a user."""
    await clear_smart_dictionary(user_id=user_id)
    return {"status": "cleared"}
