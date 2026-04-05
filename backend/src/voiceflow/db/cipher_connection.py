"""Async SQLCipher connection — aiosqlite-compatible interface.

Drop-in replacement for `aiosqlite.connect()`. Uses `asyncio.to_thread` so
all blocking sqlcipher3 I/O runs off the event loop. Encryption key comes
from DB_ENCRYPTION_KEY env/config; if not set, falls back to plain sqlite3
(development mode).
"""

import asyncio
import logging
import sqlite3
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


def _get_key() -> str | None:
    """Return encryption key from config (lazy import to avoid circular deps)."""
    from ..core.config import DB_ENCRYPTION_KEY
    return DB_ENCRYPTION_KEY or None


def _open_connection(path: str, key: str | None):
    """Open a (possibly encrypted) SQLite connection. Runs in thread."""
    if key:
        import sqlcipher3
        conn = sqlcipher3.connect(str(path))
        conn.execute(f"PRAGMA key='{key}'")
        conn.execute("PRAGMA cipher_page_size=4096")
        conn.execute("PRAGMA kdf_iter=64000")
        conn.execute("PRAGMA cipher_hmac_algorithm=HMAC_SHA512")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlcipher3.Row
    else:
        conn = sqlite3.connect(str(path))
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
    return conn


class _CursorContextManager:
    """Supports both `await conn.execute(...)` and `async with conn.execute(...) as cur:`."""

    __slots__ = ("_coro", "_cursor")

    def __init__(self, coro):
        self._coro = coro
        self._cursor = None

    def __await__(self):
        return self._coro.__await__()

    async def __aenter__(self):
        self._cursor = await self._coro
        return self._cursor

    async def __aexit__(self, *_):
        pass  # cursor has no meaningful close


class _AsyncCursor:
    """Thin async wrapper around a sqlite3.Cursor."""

    def __init__(self, cursor: sqlite3.Cursor):
        self._cursor = cursor

    @property
    def lastrowid(self) -> int | None:
        return self._cursor.lastrowid

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount

    async def fetchone(self):
        return await asyncio.to_thread(self._cursor.fetchone)

    async def fetchall(self):
        return await asyncio.to_thread(self._cursor.fetchall)

    def __aiter__(self):
        return self

    async def __anext__(self):
        row = await asyncio.to_thread(self._cursor.fetchone)
        if row is None:
            raise StopAsyncIteration
        return row


class _AsyncConnection:
    """Thin async wrapper around a sqlite3.Connection — matches aiosqlite API."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def execute(self, sql: str, params=()) -> _CursorContextManager:
        async def _run():
            cursor = await asyncio.to_thread(self._conn.execute, sql, params)
            return _AsyncCursor(cursor)
        return _CursorContextManager(_run())

    def executemany(self, sql: str, data) -> _CursorContextManager:
        async def _run():
            cursor = await asyncio.to_thread(self._conn.executemany, sql, data)
            return _AsyncCursor(cursor)
        return _CursorContextManager(_run())

    def executescript(self, script: str) -> _CursorContextManager:
        async def _run():
            cursor = await asyncio.to_thread(self._conn.executescript, script)
            return _AsyncCursor(cursor)
        return _CursorContextManager(_run())

    async def commit(self) -> None:
        await asyncio.to_thread(self._conn.commit)

    async def rollback(self) -> None:
        await asyncio.to_thread(self._conn.rollback)

    async def close(self) -> None:
        await asyncio.to_thread(self._conn.close)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        else:
            await self.commit()
        await self.close()


@asynccontextmanager
async def connect(path):
    """Async context manager — drop-in for `async with aiosqlite.connect(path)`."""
    key = _get_key()
    if key:
        logger.debug("Opening encrypted DB: %s", path)
    conn = await asyncio.to_thread(_open_connection, str(path), key)
    async_conn = _AsyncConnection(conn)
    try:
        yield async_conn
        await async_conn.commit()
    except Exception:
        await async_conn.rollback()
        raise
    finally:
        await async_conn.close()
