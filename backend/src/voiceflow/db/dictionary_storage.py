"""Dictionary, snippet, bundle, and smart-dictionary storage."""

from ._base import aiosqlite, DB_PATH


# ------------------------------------------------------------------
# Dictionary CRUD
# ------------------------------------------------------------------

async def get_dictionary(user_id: str, tenant_id: str = "default", include_smart: bool = False) -> list[dict]:
    """Return dictionary entries for user.

    include_smart=False (default): only manual entries (personal/team) — for UI display.
    include_smart=True: all entries including auto-generated smart dict — for pipeline use.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if include_smart:
            query = """SELECT * FROM user_dictionary
                       WHERE tenant_id = ? AND (scope IN ('team', 'bundle') OR user_id = ?)
                       ORDER BY length(trigger) DESC, trigger"""
        else:
            query = """SELECT * FROM user_dictionary
                       WHERE tenant_id = ? AND (scope = 'team' OR (user_id = ? AND scope = 'personal'))
                       ORDER BY scope, trigger"""
        async with db.execute(query, (tenant_id, user_id)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def add_dictionary_entry(
    trigger: str,
    replacement: str,
    user_id: str,
    scope: str = "personal",
    tenant_id: str = "default",
) -> int | None:
    """Insert a new dictionary entry. Returns the new row id."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO user_dictionary (tenant_id, user_id, trigger, replacement, scope) VALUES (?, ?, ?, ?, ?)",
            (tenant_id, user_id, trigger.strip(), replacement.strip(), scope),
        )
        await db.commit()
        return cursor.lastrowid


async def delete_dictionary_entry(entry_id: int, user_id: str, tenant_id: str = "default") -> bool:
    """Delete an entry. Users can only delete their own personal entries."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM user_dictionary WHERE id = ? AND user_id = ? AND tenant_id = ? AND scope = 'personal'",
            (entry_id, user_id, tenant_id),
        )
        await db.commit()
        return cursor.rowcount > 0


# ------------------------------------------------------------------
# Snippet CRUD
# ------------------------------------------------------------------

async def get_snippets(user_id: str, tenant_id: str = "default") -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT * FROM snippets
               WHERE tenant_id = ? AND (scope = 'team' OR user_id = ?)
               ORDER BY scope, trigger_phrase""",
            (tenant_id, user_id),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def add_snippet(
    trigger_phrase: str,
    expansion: str,
    user_id: str,
    scope: str = "personal",
    tenant_id: str = "default",
) -> int | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO snippets (tenant_id, user_id, trigger_phrase, expansion, scope) VALUES (?, ?, ?, ?, ?)",
            (tenant_id, user_id, trigger_phrase.strip(), expansion.strip(), scope),
        )
        await db.commit()
        return cursor.lastrowid


async def delete_snippet(snippet_id: int, user_id: str, tenant_id: str = "default") -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM snippets WHERE id = ? AND user_id = ? AND tenant_id = ? AND scope = 'personal'",
            (snippet_id, user_id, tenant_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def delete_snippets_by_scope(scope: str, user_id: str, tenant_id: str = "default") -> int:
    """Delete all snippets matching scope for a user. Returns deleted count."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM snippets WHERE scope = ? AND tenant_id = ? AND (user_id = ? OR user_id = '')",
            (scope, tenant_id, user_id),
        )
        await db.commit()
        return cursor.rowcount


# ------------------------------------------------------------------
# Bundle dictionary
# ------------------------------------------------------------------

async def load_bundle_entries(tenant_id: str, entries: list[dict]) -> int:
    """Replace bundle-scope dictionary entries for a tenant. Returns count inserted."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM user_dictionary WHERE tenant_id = ? AND scope = 'bundle'", (tenant_id,)
        )
        await db.executemany(
            "INSERT OR IGNORE INTO user_dictionary (tenant_id, user_id, trigger, replacement, scope) VALUES (?, ?, ?, ?, 'bundle')",
            [(tenant_id, "", e["trigger"], e["replacement"]) for e in entries],
        )
        await db.commit()
    return len(entries)


async def clear_bundle_entries(tenant_id: str) -> None:
    """Remove all bundle-scope dictionary entries for a tenant."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM user_dictionary WHERE tenant_id = ? AND scope = 'bundle'", (tenant_id,)
        )
        await db.commit()


async def count_bundle_entries(tenant_id: str = "default") -> int:
    """Return number of bundle-scope entries for a tenant."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM user_dictionary WHERE tenant_id = ? AND scope = 'bundle'",
            (tenant_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


# ------------------------------------------------------------------
# Context / smart dictionary
# ------------------------------------------------------------------

async def get_context_status(user_id: str) -> dict:
    """Return smart dictionary + symbol index counts for a user."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM user_dictionary WHERE user_id = ? AND scope = 'smart'", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            n = row[0] if row else 0
        async with db.execute(
            "SELECT COUNT(*), MAX(indexed_at) FROM symbol_index_v2 WHERE user_id = ?", (user_id,)
        ) as cursor:
            row2 = await cursor.fetchone()
            sym_count = row2[0] if row2 else 0
            last_indexed_at = row2[1] if row2 else None
    return {"smart_count": n, "symbol_count": sym_count, "last_indexed_at": last_indexed_at}


async def get_context_projects(user_id: str) -> dict:
    """Return indexed projects with symbol counts and smart dictionary word count."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT project_path, COUNT(*) FROM symbol_index WHERE user_id = ? GROUP BY project_path",
            (user_id,),
        ) as cursor:
            symbol_rows = {row[0]: row[1] for row in await cursor.fetchall()}
        async with db.execute(
            "SELECT COUNT(*) FROM user_dictionary WHERE user_id = ? AND scope = 'smart'", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            smart_total = row[0] if row else 0
    return {"symbol_rows": symbol_rows, "smart_total": smart_total}


async def clear_smart_dictionary(user_id: str, tenant_id: str = "default") -> None:
    """Remove smart-scope dictionary entries for a user."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM user_dictionary WHERE user_id = ? AND tenant_id = ? AND scope = 'smart'",
            (user_id, tenant_id),
        )
        await db.commit()


async def get_dictionary_triggers(user_id: str) -> set[str]:
    """Return all existing trigger strings for a user (for dedup checks)."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT trigger FROM user_dictionary WHERE user_id = ?", (user_id,)
        ) as cursor:
            return {row[0] for row in await cursor.fetchall()}


async def bulk_add_smart_entries(
    user_id: str, tenant_id: str, pairs: list[tuple[str, str]]
) -> int:
    """Insert (trigger, replacement) pairs with scope=smart. Skips existing triggers. Returns added count."""
    existing = await get_dictionary_triggers(user_id)
    to_insert = [
        (tenant_id, user_id, trigger, replacement, "smart")
        for trigger, replacement in pairs
        if trigger and replacement and trigger not in existing
    ]
    if not to_insert:
        return 0
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executemany(
            "INSERT INTO user_dictionary (tenant_id, user_id, trigger, replacement, scope) VALUES (?, ?, ?, ?, ?)",
            to_insert,
        )
        await db.commit()
    return len(to_insert)
