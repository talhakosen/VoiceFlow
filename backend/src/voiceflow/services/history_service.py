"""HistoryService — transcription history business logic."""

import logging

from ..db import get_history, clear_history, append_audit_log

logger = logging.getLogger(__name__)


async def fetch_history(
    limit: int,
    offset: int,
    requested_user_id: str | None,
    caller_user_id: str | None,
    role: str,
    tenant_id: str,
) -> dict:
    """Return paginated history, scoped by role.

    Raises PermissionError if a non-admin requests another user's history.
    """
    if requested_user_id is not None and requested_user_id != caller_user_id:
        if role not in ("admin", "superadmin"):
            raise PermissionError("Cannot access other users' history")

    # Non-admin without explicit user_id: scope to self
    effective_user_id = requested_user_id
    if effective_user_id is None and role not in ("admin", "superadmin") and caller_user_id:
        effective_user_id = caller_user_id

    rows = await get_history(
        limit=limit,
        offset=offset,
        user_id=effective_user_id,
        tenant_id=tenant_id,
    )
    return {"items": rows, "count": len(rows)}


async def wipe_history(tenant_id: str, user_id: str) -> None:
    """Clear all history and append audit log."""
    await clear_history()
    await append_audit_log(
        tenant_id=tenant_id,
        action="history_cleared",
        user_id=user_id,
    )
