"""Admin endpoints — user management (admin+ only)."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..api.auth import verify_api_key
from ..db import list_users, update_user_role, deactivate_user
from ..services.auth_service import require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", dependencies=[Depends(verify_api_key)])

_VALID_ROLES = {"member", "admin", "superadmin"}


class RoleUpdateRequest(BaseModel):
    role: str


@router.get("/users", dependencies=[require_role("admin")])
async def get_users(request: Request):
    """List all users in the caller's tenant."""
    tenant_id = getattr(request.state, "tenant_id", "default")
    return await list_users(tenant_id)


@router.put("/users/{user_id}/role", dependencies=[require_role("admin")])
async def set_user_role(user_id: str, body: RoleUpdateRequest, request: Request):
    """Change a user's role within the same tenant."""
    if body.role not in _VALID_ROLES:
        raise HTTPException(status_code=422, detail=f"Invalid role. Must be one of: {sorted(_VALID_ROLES)}")
    tenant_id = getattr(request.state, "tenant_id", "default")
    updated = await update_user_role(user_id, body.role, tenant_id)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found in this tenant")
    return {"user_id": user_id, "role": body.role}


@router.delete("/users/{user_id}", dependencies=[require_role("admin")])
async def remove_user(user_id: str, request: Request):
    """Soft-delete a user (is_active=0) within the same tenant."""
    tenant_id = getattr(request.state, "tenant_id", "default")
    deactivated = await deactivate_user(user_id, tenant_id)
    if not deactivated:
        raise HTTPException(status_code=404, detail="User not found in this tenant")
    return {"user_id": user_id, "is_active": False}
