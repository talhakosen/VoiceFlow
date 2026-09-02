"""Dictionary, snippet, bundle, and smart-dictionary storage."""

import logging

from ._base import aiosqlite, DB_PATH

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Dictionary cache
# ------------------------------------------------------------------
# Sözlük her diktede okunuyordu: include_smart=True 78.107 kayıt → 285ms,
# yani metin işleme aşamasının TAMAMI (ölçüldü 2026-09-02). Sözlük ise
# nadiren değişiyor — kullanıcı kelime eklediğinde, bundle yüklendiğinde
# veya smart index yeniden kurulduğunda.
#
# Cache süreç içi ve yazma anında geçersiz kılınıyor. `_version` her
# geçersiz kılmada artar; pipeline Aho-Corasick automaton'ını bu sürüme
# göre yeniden kuruyor (eskiden kayıt SAYISINA bakıyordu — sayı değişmeden
# içerik değişirse automaton bayat kalıyordu).

_cache: dict[tuple[str, str, bool], list[dict]] = {}
_version: int = 0

# Sunucu modunda kullanıcı başına bir giriş birikir; 78K kayıtlık bir sözlük
# ~25MB tutuyor, sınırsız büyümesin. Local modda tek kullanıcı var, bu sınır
# hiç devreye girmez.
_MAX_CACHED_KEYS = 8


def dictionary_version() -> int:
    """Her geçersiz kılmada artan sürüm — automaton cache'i için."""
    return _version


def invalidate_dictionary_cache() -> None:
    """Sözlüğü değiştiren HER yazma bunu çağırmalı."""
    global _version
    _cache.clear()
    _version += 1


# ------------------------------------------------------------------
# Dictionary CRUD
# ------------------------------------------------------------------

async def get_dictionary(user_id: str, tenant_id: str = "default", include_smart: bool = False) -> list[dict]:
    """Return dictionary entries for user.

    include_smart=False (default): only manual entries (personal/team) — for UI display.
    include_smart=True: all entries including auto-generated smart dict — for pipeline use.

    Sonuç cache'lenir. Dönen liste PAYLAŞILIR — çağıran tarafta değiştirme;
    78K kaydı her çağrıda kopyalamak cache'in amacını yok eder.
    """
    key = (tenant_id, user_id, include_smart)
    if (cached := _cache.get(key)) is not None:
        return cached

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
            entries = [dict(row) for row in rows]

    if len(_cache) >= _MAX_CACHED_KEYS:
        _cache.pop(next(iter(_cache)))  # FIFO — en eski giriş
    _cache[key] = entries
    logger.debug("Dictionary cached: %d entries (smart=%s)", len(entries), include_smart)
    return entries


async def last_active_user_id(tenant_id: str = "default") -> str | None:
    """En son dikte yapan kullanıcı — startup'ta kimin sözlüğünü ısıtacağımızı bilmek için.

    Local modda tek kullanıcı var; sunucu modunda ısınma zaten anlamsız
    (hangi kullanıcının geleceği bilinmez) ama yanlış tahmin de zarar vermez,
    sadece bir kereliğine kullanılmayan bir cache girişi oluşur.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """SELECT user_id FROM transcriptions
               WHERE tenant_id = ? AND user_id IS NOT NULL AND user_id != ''
               ORDER BY id DESC LIMIT 1""",
            (tenant_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def warm_dictionary_cache(user_id: str, tenant_id: str = "default") -> int:
    """Sözlüğü startup'ta cache'e al — ilk dikte 250ms beklemesin.

    Bundle auto-load'dan SONRA çağrılmalı, yoksa yüklenen bundle cache'i
    hemen geçersiz kılar ve ısınma boşa gider.
    """
    entries = await get_dictionary(user_id=user_id, tenant_id=tenant_id, include_smart=True)
    logger.info("Dictionary cache warmed: %d entries", len(entries))
    return len(entries)


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
    invalidate_dictionary_cache()
    return cursor.lastrowid


async def delete_dictionary_entry(entry_id: int, user_id: str, tenant_id: str = "default") -> bool:
    """Delete an entry. Users can only delete their own personal entries."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM user_dictionary WHERE id = ? AND user_id = ? AND tenant_id = ? AND scope = 'personal'",
            (entry_id, user_id, tenant_id),
        )
        await db.commit()
    invalidate_dictionary_cache()
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
    invalidate_dictionary_cache()
    return len(entries)


async def clear_bundle_entries(tenant_id: str) -> None:
    """Remove all bundle-scope dictionary entries for a tenant."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM user_dictionary WHERE tenant_id = ? AND scope = 'bundle'", (tenant_id,)
        )
        await db.commit()
    invalidate_dictionary_cache()


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
    invalidate_dictionary_cache()


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
    invalidate_dictionary_cache()
    return len(to_insert)
