"""DictionaryService — dictionary CRUD business logic."""

import json
import logging
from pathlib import Path

from ..db import (
    get_dictionary, add_dictionary_entry, delete_dictionary_entry,
    load_bundle_entries, clear_bundle_entries,
)

logger = logging.getLogger(__name__)

_BUNDLE_PATH = Path(__file__).parents[4] / "ml" / "dictionary" / "it_bundle_full.json"


# ── Dictionary ──────────────────────────────────────────────────────

async def list_dictionary(user_id: str) -> dict:
    entries = await get_dictionary(user_id=user_id)
    return {"items": entries, "count": len(entries)}


async def create_dictionary_entry(trigger: str, replacement: str, user_id: str, scope: str) -> dict:
    """Validate and create a dictionary entry. Raises ValueError on bad input."""
    if not trigger.strip() or not replacement.strip():
        raise ValueError("trigger and replacement must not be empty")
    if scope not in ("personal", "team"):
        raise ValueError("scope must be 'personal' or 'team'")
    entry_id = await add_dictionary_entry(
        trigger=trigger,
        replacement=replacement,
        user_id=user_id,
        scope=scope,
    )
    return {"id": entry_id, "trigger": trigger, "replacement": replacement, "scope": scope}


async def remove_dictionary_entry(entry_id: int, user_id: str) -> None:
    """Delete a dictionary entry. Raises LookupError if not found/owned."""
    deleted = await delete_dictionary_entry(entry_id=entry_id, user_id=user_id)
    if not deleted:
        raise LookupError("Entry not found or not yours")


# ── Dictionary bundle ────────────────────────────────────────────────

async def load_dict_bundle(tenant_id: str = "default") -> dict:
    """Load IT Turkish phonetics bundle. Raises FileNotFoundError if missing."""
    if not _BUNDLE_PATH.exists():
        raise FileNotFoundError("Bundle file not found")
    with open(_BUNDLE_PATH, encoding="utf-8") as f:
        entries = json.load(f)
    count = await load_bundle_entries(tenant_id=tenant_id, entries=entries)
    return {"status": "loaded", "count": count}


async def wipe_dict_bundle(tenant_id: str = "default") -> dict:
    await clear_bundle_entries(tenant_id=tenant_id)
    return {"status": "cleared"}
