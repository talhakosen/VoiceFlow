"""symbol/lookup.py — Fuzzy symbol lookup from symbol_index_v2."""

from __future__ import annotations

import aiosqlite

from ..core.config import DB_PATH


async def lookup_symbol(query: str, user_id: str, limit: int = 5) -> list[dict]:
    """Fuzzy symbol lookup from symbol_index_v2. Returns enriched results."""
    query = query.strip()
    if not query:
        return []

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Exact match (case-insensitive)
        async with db.execute(
            """SELECT symbol_name, symbol_type, file_path, line_number,
                      end_line, signature, parent_symbol, parent_class,
                      conformances, return_type
               FROM symbol_index_v2
               WHERE user_id = ? AND LOWER(symbol_name) = LOWER(?)
               ORDER BY CASE symbol_type WHEN 'class' THEN 0 WHEN 'struct' THEN 1 WHEN 'protocol' THEN 2 ELSE 3 END
               LIMIT ?""",
            (user_id, query, limit),
        ) as cursor:
            rows = [dict(r) for r in await cursor.fetchall()]

        if rows:
            return rows

        # Prefix match
        async with db.execute(
            """SELECT symbol_name, symbol_type, file_path, line_number,
                      end_line, signature, parent_symbol, parent_class,
                      conformances, return_type
               FROM symbol_index_v2
               WHERE user_id = ? AND LOWER(symbol_name) LIKE LOWER(?)
               ORDER BY length(symbol_name)
               LIMIT ?""",
            (user_id, f"{query}%", limit),
        ) as cursor:
            rows = [dict(r) for r in await cursor.fetchall()]

        if rows:
            return rows

        # Substring match
        async with db.execute(
            """SELECT symbol_name, symbol_type, file_path, line_number,
                      end_line, signature, parent_symbol, parent_class,
                      conformances, return_type
               FROM symbol_index_v2
               WHERE user_id = ? AND LOWER(symbol_name) LIKE LOWER(?)
               ORDER BY length(symbol_name)
               LIMIT ?""",
            (user_id, f"%{query}%", limit),
        ) as cursor:
            return [dict(r) for r in await cursor.fetchall()]
