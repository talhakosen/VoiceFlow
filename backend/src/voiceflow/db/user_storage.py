"""User account storage."""

import uuid

from ._base import aiosqlite, DB_PATH


async def create_user(
    email: str,
    password_hash: str,
    tenant_id: str = "default",
    role: str = "member",
) -> str:
    """Insert a new user. Returns the new user id (UUID)."""
    user_id = str(uuid.uuid4())
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO users (id, email, password_hash, tenant_id, role) VALUES (?, ?, ?, ?, ?)",
            (user_id, email, password_hash, tenant_id, role),
        )
        await db.commit()
    return user_id


async def get_user_by_email(email: str) -> dict | None:
    """Return user row as dict or None."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE email = ?", (email,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_user_by_id(user_id: str) -> dict | None:
    """Return user row as dict or None."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def list_users(tenant_id: str) -> list[dict]:
    """Return all users for a tenant."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, email, tenant_id, role, is_active, created_at FROM users WHERE tenant_id = ? ORDER BY created_at",
            (tenant_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def update_user_role(user_id: str, role: str, tenant_id: str) -> bool:
    """Update role for a user within the same tenant. Returns True if updated."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "UPDATE users SET role = ? WHERE id = ? AND tenant_id = ?",
            (role, user_id, tenant_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def deactivate_user(user_id: str, tenant_id: str) -> bool:
    """Soft-delete: set is_active=0. Returns True if updated."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "UPDATE users SET is_active = 0 WHERE id = ? AND tenant_id = ?",
            (user_id, tenant_id),
        )
        await db.commit()
        return cursor.rowcount > 0
