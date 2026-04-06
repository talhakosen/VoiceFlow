"""Auth endpoints: register, login, refresh, me."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from jose import JWTError
from pydantic import BaseModel, field_validator

from ..core.rate_limit import limiter, RATE_LIMIT_AUTH
from ..services.user_service import (
    register_user, authenticate, refresh_access, logout_token, get_authenticated_user,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])


# --- Schemas ---

class RegisterRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def email_valid(cls, v: str) -> str:
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email address")
        return v.lower().strip()

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def email_normalize(cls, v: str) -> str:
        return v.lower().strip()


class RefreshRequest(BaseModel):
    refresh_token: str


# --- Shared dependency ---

async def get_current_user(authorization: str = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        return await get_authenticated_user(token)
    except PermissionError as e:
        raise HTTPException(status_code=401, detail=str(e))


# --- Endpoints ---

@router.post("/register", status_code=201)
@limiter.limit(RATE_LIMIT_AUTH)
async def register(request: Request, body: RegisterRequest):
    try:
        return await register_user(email=body.email, password=body.password)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/login")
@limiter.limit(RATE_LIMIT_AUTH)
async def login(request: Request, body: LoginRequest):
    try:
        return await authenticate(email=body.email, password=body.password)
    except PermissionError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/refresh")
async def refresh(body: RefreshRequest):
    try:
        return await refresh_access(body.refresh_token)
    except JWTError as e:
        raise HTTPException(status_code=401, detail=str(e) or "Invalid or expired refresh token")
    except LookupError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    return {
        "user_id": current_user["id"],
        "email": current_user["email"],
        "tenant_id": current_user["tenant_id"],
        "role": current_user["role"],
    }


@router.post("/logout")
@limiter.limit(RATE_LIMIT_AUTH)
async def logout(
    request: Request,
    authorization: str = Header(default=None),
):
    """Revoke the current access token. Client should also discard the refresh token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    await logout_token(token)
    return {"detail": "logged out"}
