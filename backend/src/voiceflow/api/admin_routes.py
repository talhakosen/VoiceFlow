"""Admin endpoints — user management (admin+ only)."""

import logging

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

from ..api.auth import verify_api_key
from ..db import list_users, update_user_role, deactivate_user, get_tenant_stats
from ..services.auth_service import require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", dependencies=[Depends(verify_api_key)])

_VALID_ROLES = {"member", "admin", "superadmin"}


class RoleUpdateRequest(BaseModel):
    role: str


# ------------------------------------------------------------------
# JSON API (mevcut — kırılmaz)
# ------------------------------------------------------------------

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


@router.get("/stats", dependencies=[require_role("admin")])
async def admin_stats(request: Request):
    """Tenant istatistikleri — JSON."""
    tenant_id = getattr(request.state, "tenant_id", "default")
    return await get_tenant_stats(tenant_id)


# ------------------------------------------------------------------
# HTML UI
# ------------------------------------------------------------------

def _get_templates(request: Request):
    return request.app.state.templates


@router.get("/", response_class=HTMLResponse, dependencies=[require_role("admin")])
async def admin_dashboard(request: Request):
    """Admin dashboard — kullanıcı listesi + istatistikler."""
    tenant_id = getattr(request.state, "tenant_id", "default")
    users = await list_users(tenant_id)
    stats = await get_tenant_stats(tenant_id)
    templates = _get_templates(request)
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "users": users,
            "stats": stats,
            "tenant_id": tenant_id,
            "valid_roles": sorted(_VALID_ROLES),
        },
    )


@router.post("/users/{user_id}/role", response_class=HTMLResponse, dependencies=[require_role("admin")])
async def admin_change_role_form(
    request: Request,
    user_id: str,
    role: str = Form(...),
):
    """Form submit: rol değiştir → dashboard'a yönlendir."""
    if role not in _VALID_ROLES:
        raise HTTPException(status_code=422, detail=f"Invalid role: {role}")
    tenant_id = getattr(request.state, "tenant_id", "default")
    updated = await update_user_role(user_id, role, tenant_id)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return RedirectResponse(url="/admin/", status_code=303)


@router.post("/users/{user_id}/deactivate", response_class=HTMLResponse, dependencies=[require_role("admin")])
async def admin_deactivate_form(request: Request, user_id: str):
    """Form submit: kullanıcıyı deaktive et → dashboard'a yönlendir."""
    tenant_id = getattr(request.state, "tenant_id", "default")
    deactivated = await deactivate_user(user_id, tenant_id)
    if not deactivated:
        raise HTTPException(status_code=404, detail="User not found")
    return RedirectResponse(url="/admin/", status_code=303)
