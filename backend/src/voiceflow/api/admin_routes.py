"""Admin endpoints — user management (admin+ only)."""

import logging

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

from ..api.auth import verify_api_key
from ..services.admin_service import (
    VALID_ROLES,
    fetch_users, change_user_role, deactivate, fetch_stats, fetch_audit_log, wipe_user_data,
)
from ..services.auth_service import require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", dependencies=[Depends(verify_api_key)])


class RoleUpdateRequest(BaseModel):
    role: str


# ------------------------------------------------------------------
# JSON API (mevcut — kırılmaz)
# ------------------------------------------------------------------

@router.get("/users", dependencies=[require_role("admin")])
async def get_users(request: Request):
    """List all users in the caller's tenant."""
    tenant_id = getattr(request.state, "tenant_id", "default")
    return await fetch_users(tenant_id)


@router.put("/users/{user_id}/role", dependencies=[require_role("admin")])
async def set_user_role(user_id: str, body: RoleUpdateRequest, request: Request):
    """Change a user's role within the same tenant."""
    tenant_id = getattr(request.state, "tenant_id", "default")
    try:
        return await change_user_role(user_id, body.role, tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/users/{user_id}", dependencies=[require_role("admin")])
async def remove_user(user_id: str, request: Request):
    """Soft-delete a user (is_active=0) within the same tenant."""
    tenant_id = getattr(request.state, "tenant_id", "default")
    try:
        return await deactivate(user_id, tenant_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/stats", dependencies=[require_role("admin")])
async def admin_stats(request: Request):
    """Tenant istatistikleri — JSON."""
    tenant_id = getattr(request.state, "tenant_id", "default")
    return await fetch_stats(tenant_id)


@router.get("/audit-log", dependencies=[require_role("admin")])
async def get_audit_log_endpoint(
    request: Request,
    limit: int = Query(default=200, le=2000),
    offset: int = 0,
):
    """Tenant audit log — admin only, newest first."""
    tenant_id = getattr(request.state, "tenant_id", "default")
    return await fetch_audit_log(tenant_id, limit=limit, offset=offset)


@router.delete("/users/{user_id}/data", dependencies=[require_role("admin")])
async def delete_user_data_endpoint(user_id: str, request: Request):
    """KVKK: kalıcı olarak tüm kişisel veriyi sil (transkript, sözlük, snippet, hesap)."""
    tenant_id = getattr(request.state, "tenant_id", "default")
    actor_id = getattr(request.state, "user_id", "")
    return await wipe_user_data(user_id=user_id, tenant_id=tenant_id, actor_id=actor_id)


# ------------------------------------------------------------------
# HTML UI
# ------------------------------------------------------------------

def _get_templates(request: Request):
    return request.app.state.templates


@router.get("/", response_class=HTMLResponse, dependencies=[require_role("admin")])
async def admin_dashboard(request: Request):
    """Admin dashboard — kullanıcı listesi + istatistikler."""
    tenant_id = getattr(request.state, "tenant_id", "default")
    users = await fetch_users(tenant_id)
    stats = await fetch_stats(tenant_id)
    templates = _get_templates(request)
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "users": users,
            "stats": stats,
            "tenant_id": tenant_id,
            "valid_roles": sorted(VALID_ROLES),
        },
    )


@router.post("/users/{user_id}/role", response_class=HTMLResponse, dependencies=[require_role("admin")])
async def admin_change_role_form(
    request: Request,
    user_id: str,
    role: str = Form(...),
):
    """Form submit: rol değiştir → dashboard'a yönlendir."""
    tenant_id = getattr(request.state, "tenant_id", "default")
    try:
        await change_user_role(user_id, role, tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return RedirectResponse(url="/admin/", status_code=303)


@router.post("/users/{user_id}/deactivate", response_class=HTMLResponse, dependencies=[require_role("admin")])
async def admin_deactivate_form(request: Request, user_id: str):
    """Form submit: kullanıcıyı deaktive et → dashboard'a yönlendir."""
    tenant_id = getattr(request.state, "tenant_id", "default")
    try:
        await deactivate(user_id, tenant_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return RedirectResponse(url="/admin/", status_code=303)
