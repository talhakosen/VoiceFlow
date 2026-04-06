"""DictionaryService — dictionary and snippet CRUD business logic."""

import json
import logging
from pathlib import Path

from ..db import (
    get_dictionary, add_dictionary_entry, delete_dictionary_entry,
    get_snippets, add_snippet, delete_snippet, delete_snippets_by_scope,
    load_bundle_entries, clear_bundle_entries,
)

logger = logging.getLogger(__name__)

_SNIPPET_PACKS: dict[str, str] = {
    "office": "office_pack.json",
    "engineering": "engineering_pack.json",
}

_BUNDLE_PATH = Path(__file__).parents[4] / "ml" / "dictionary" / "it_bundle_full.json"
_PACK_DIR = Path(__file__).parents[5] / "ml" / "snippets"


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


# ── Snippets ─────────────────────────────────────────────────────────

async def list_snippets(user_id: str) -> dict:
    items = await get_snippets(user_id=user_id)
    return {"items": items, "count": len(items)}


async def create_snippet(trigger_phrase: str, expansion: str, user_id: str, scope: str) -> dict:
    """Validate and create a snippet. Raises ValueError on bad input."""
    if not trigger_phrase.strip() or not expansion.strip():
        raise ValueError("trigger_phrase and expansion must not be empty")
    if scope not in ("personal", "team"):
        raise ValueError("scope must be 'personal' or 'team'")
    snippet_id = await add_snippet(
        trigger_phrase=trigger_phrase,
        expansion=expansion,
        user_id=user_id,
        scope=scope,
    )
    return {"id": snippet_id, "trigger_phrase": trigger_phrase, "expansion": expansion, "scope": scope}


async def remove_snippet(snippet_id: int, user_id: str) -> None:
    """Delete a snippet. Raises LookupError if not found/owned."""
    deleted = await delete_snippet(snippet_id=snippet_id, user_id=user_id)
    if not deleted:
        raise LookupError("Snippet not found or not yours")


# ── Snippet packs ────────────────────────────────────────────────────

async def load_snippet_pack(pack_name: str, user_id: str) -> dict:
    """Load a pre-built snippet pack (idempotent). Raises ValueError/FileNotFoundError."""
    if pack_name not in _SNIPPET_PACKS:
        raise ValueError(f"Unknown pack: {pack_name}. Available: {list(_SNIPPET_PACKS)}")

    scope = f"pack_{pack_name}"
    pack_path = _PACK_DIR / _SNIPPET_PACKS[pack_name]
    if not pack_path.exists():
        raise FileNotFoundError("Pack file not found")

    with open(pack_path, encoding="utf-8") as f:
        items = json.load(f)

    existing = await get_snippets(user_id=user_id)
    existing_triggers = {s["trigger_phrase"] for s in existing if s.get("scope") == scope}

    added = 0
    for item in items:
        trigger = item["trigger_phrase"]
        if trigger not in existing_triggers:
            await add_snippet(
                trigger_phrase=trigger,
                expansion=item["expansion"],
                user_id=user_id,
                scope=scope,
            )
            added += 1

    return {"status": "loaded", "pack": pack_name, "added": added, "total": len(items)}


async def clear_snippet_pack(pack_name: str, user_id: str, tenant_id: str = "default") -> dict:
    """Remove all entries from a snippet pack."""
    if pack_name not in _SNIPPET_PACKS:
        raise ValueError(f"Unknown pack: {pack_name}")

    scope = f"pack_{pack_name}"
    deleted = await delete_snippets_by_scope(scope=scope, user_id=user_id, tenant_id=tenant_id)
    return {"status": "cleared", "pack": pack_name, "deleted": deleted}
