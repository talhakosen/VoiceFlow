"""AdminService — user management and tenant admin business logic."""

import logging

from ..db import (
    list_users, update_user_role, deactivate_user, get_tenant_stats,
    append_audit_log, get_audit_log, delete_user_data,
)

logger = logging.getLogger(__name__)

VALID_ROLES = frozenset({"member", "admin", "superadmin"})


async def fetch_users(tenant_id: str) -> list:
    return await list_users(tenant_id)


async def change_user_role(user_id: str, role: str, tenant_id: str) -> dict:
    """Validate and update a user's role. Raises ValueError/LookupError."""
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role. Must be one of: {sorted(VALID_ROLES)}")
    updated = await update_user_role(user_id, role, tenant_id)
    if not updated:
        raise LookupError("User not found in this tenant")
    return {"user_id": user_id, "role": role}


async def deactivate(user_id: str, tenant_id: str) -> dict:
    """Soft-delete a user. Raises LookupError if not found."""
    deactivated = await deactivate_user(user_id, tenant_id)
    if not deactivated:
        raise LookupError("User not found in this tenant")
    return {"user_id": user_id, "is_active": False}


async def fetch_stats(tenant_id: str) -> dict:
    return await get_tenant_stats(tenant_id)


async def fetch_audit_log(tenant_id: str, limit: int = 200, offset: int = 0) -> list:
    return await get_audit_log(tenant_id, limit=limit, offset=offset)


async def wipe_user_data(user_id: str, tenant_id: str, actor_id: str) -> dict:
    """KVKK: permanently delete all personal data + audit log the action."""
    result = await delete_user_data(user_id, tenant_id)
    await append_audit_log(
        tenant_id=tenant_id,
        action="user_data_deleted",
        user_id=actor_id,
        target=user_id,
    )
    return result
