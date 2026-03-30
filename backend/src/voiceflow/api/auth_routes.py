"""Auth endpoints: register, login, refresh, me."""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, field_validator
from jose import JWTError

from ..db import create_user, get_user_by_email, get_user_by_id, append_audit_log
from ..services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
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
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Not an access token")
    user_id = payload.get("sub")
    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# --- Endpoints ---

@router.post("/register", status_code=201)
async def register(body: RegisterRequest):
    existing = await get_user_by_email(body.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    loop = asyncio.get_running_loop()
    password_hash = await loop.run_in_executor(None, hash_password, body.password)
    tenant_id = "default"
    user_id = await create_user(
        email=body.email,
        password_hash=password_hash,
        tenant_id=tenant_id,
    )
    return {"user_id": user_id, "email": body.email, "tenant_id": tenant_id}


@router.post("/login")
async def login(body: LoginRequest):
    user = await get_user_by_email(body.email)
    loop = asyncio.get_running_loop()
    is_valid = user and await loop.run_in_executor(
        None, verify_password, body.password, user["password_hash"]
    )
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token(
        user_id=user["id"],
        tenant_id=user["tenant_id"],
        role=user["role"],
    )
    refresh_token = create_refresh_token(user_id=user["id"])
    await append_audit_log(
        tenant_id=user["tenant_id"],
        action="login",
        user_id=user["id"],
        target=body.email,
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh")
async def refresh(body: RefreshRequest):
    try:
        payload = decode_token(body.refresh_token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Not a refresh token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    access_token = create_access_token(
        user_id=user["id"],
        tenant_id=user["tenant_id"],
        role=user["role"],
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    return {
        "user_id": current_user["id"],
        "email": current_user["email"],
        "tenant_id": current_user["tenant_id"],
        "role": current_user["role"],
    }
