"""symbol/lookup.py — Fuzzy symbol lookup from symbol_index_v2."""

from __future__ import annotations

from ..db.storage import lookup_symbol_exact, lookup_symbol_prefix, lookup_symbol_substring


async def lookup_symbol(query: str, user_id: str, limit: int = 5) -> list[dict]:
    """Fuzzy symbol lookup from symbol_index_v2. Returns enriched results."""
    query = query.strip()
    if not query:
        return []

    rows = await lookup_symbol_exact(query=query, user_id=user_id, limit=limit)
    if rows:
        return rows

    rows = await lookup_symbol_prefix(query=query, user_id=user_id, limit=limit)
    if rows:
        return rows

    return await lookup_symbol_substring(query=query, user_id=user_id, limit=limit)
