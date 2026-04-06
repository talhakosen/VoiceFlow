"""JWT token blacklist storage."""

from ._base import aiosqlite, DB_PATH


async def revoke_token(jti: str, expires_at: str) -> None:
    """Add token JTI to blacklist. expires_at is ISO 8601 UTC string."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO token_blacklist (jti, expires_at) VALUES (?, ?)",
            (jti, expires_at),
        )
        await db.commit()


async def is_token_revoked(jti: str) -> bool:
    """Return True if token JTI is in the blacklist."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM token_blacklist WHERE jti = ?", (jti,)
        ) as cursor:
            return (await cursor.fetchone()) is not None


async def purge_expired_tokens() -> int:
    """Delete blacklist entries whose JWT has already expired. Returns count."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM token_blacklist WHERE expires_at < datetime('now')"
        )
        await db.commit()
        return cursor.rowcount
