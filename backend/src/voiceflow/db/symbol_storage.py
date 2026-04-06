"""Symbol index storage (v1 + v2)."""

import json

from ._base import aiosqlite, DB_PATH


async def clear_symbol_indexes(user_id: str, project_path: str) -> None:
    """Clear both symbol_index and symbol_index_v2 for a user+project."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM symbol_index_v2 WHERE user_id = ? AND project_path = ?",
            (user_id, project_path),
        )
        await db.execute(
            "DELETE FROM symbol_index WHERE user_id = ? AND project_path = ?",
            (user_id, project_path),
        )
        await db.commit()


async def clear_symbol_index_v2(user_id: str, project_path: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM symbol_index_v2 WHERE user_id = ? AND project_path = ?",
            (user_id, project_path),
        )
        await db.commit()


async def save_symbol_batch(
    user_id: str,
    project_path: str,
    symbols: list,  # list[SymbolInfo] — avoid circular import
) -> None:
    """Bulk insert symbols into symbol_index_v2 and symbol_index (compat)."""
    async with aiosqlite.connect(DB_PATH) as db:
        for sym in symbols:
            await db.execute(
                """INSERT INTO symbol_index_v2
                   (user_id, project_path, file_path, symbol_type, symbol_name,
                    line_number, end_line, signature, parent_symbol, parent_class,
                    conformances, return_type, properties, imports, decorators,
                    visibility, is_static)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    user_id, project_path, sym.file_path, sym.symbol_type, sym.symbol_name,
                    sym.line_number, sym.end_line, sym.signature, sym.parent_symbol,
                    sym.parent_class, sym.conformances, sym.return_type,
                    json.dumps(sym.properties, ensure_ascii=False) if sym.properties else None,
                    json.dumps(sym.imports, ensure_ascii=False) if sym.imports else None,
                    json.dumps(sym.decorators, ensure_ascii=False) if sym.decorators else None,
                    sym.visibility, int(sym.is_static),
                ),
            )
            await db.execute(
                """INSERT OR IGNORE INTO symbol_index
                   (user_id, project_path, file_path, symbol_type, symbol_name, line_number)
                   VALUES (?,?,?,?,?,?)""",
                (user_id, project_path, sym.file_path, sym.symbol_type, sym.symbol_name, sym.line_number),
            )
        await db.commit()


async def get_symbol_index_file_paths(user_id: str) -> list[dict]:
    """Return (project_path, file_path) rows from symbol_index for a user."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT DISTINCT project_path, file_path FROM symbol_index WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            return [dict(r) for r in await cursor.fetchall()]


async def get_symbols_for_matching(
    user_id: str,
    symbol_types: tuple[str, ...] = ("class", "struct", "protocol", "enum", "interface", "object", "module"),
) -> list[dict]:
    """Return symbols from symbol_index for fuzzy/phonetic matching."""
    placeholders = ",".join("?" * len(symbol_types))
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            f"""SELECT symbol_name, file_path, line_number, symbol_type
                FROM symbol_index WHERE user_id = ?
                AND symbol_type IN ({placeholders})""",
            (user_id, *symbol_types),
        ) as cursor:
            return [dict(r) for r in await cursor.fetchall()]


async def lookup_symbol_exact(query: str, user_id: str, limit: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
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
            return [dict(r) for r in await cursor.fetchall()]


async def lookup_symbol_prefix(query: str, user_id: str, limit: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT symbol_name, symbol_type, file_path, line_number,
                      end_line, signature, parent_symbol, parent_class,
                      conformances, return_type
               FROM symbol_index_v2
               WHERE user_id = ? AND LOWER(symbol_name) LIKE LOWER(?)
               ORDER BY length(symbol_name) LIMIT ?""",
            (user_id, f"{query}%", limit),
        ) as cursor:
            return [dict(r) for r in await cursor.fetchall()]


async def lookup_symbol_substring(query: str, user_id: str, limit: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT symbol_name, symbol_type, file_path, line_number,
                      end_line, signature, parent_symbol, parent_class,
                      conformances, return_type
               FROM symbol_index_v2
               WHERE user_id = ? AND LOWER(symbol_name) LIKE LOWER(?)
               ORDER BY length(symbol_name) LIMIT ?""",
            (user_id, f"%{query}%", limit),
        ) as cursor:
            return [dict(r) for r in await cursor.fetchall()]


async def get_symbols_for_notes(user_id: str, project_path: str) -> list[dict]:
    """Fetch enriched symbols for project-notes generation."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT symbol_type, symbol_name, file_path, line_number,
                      parent_class, conformances, signature, imports
               FROM symbol_index_v2
               WHERE user_id = ? AND project_path = ?
               ORDER BY symbol_type, symbol_name""",
            (user_id, project_path),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
