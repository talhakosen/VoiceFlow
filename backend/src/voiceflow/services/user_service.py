"""UserService — authentication and user lifecycle business logic."""

import asyncio
import logging
from datetime import datetime, timezone

from jose import JWTError

from ..db import (
    create_user, get_user_by_email, get_user_by_id,
    append_audit_log, revoke_token, is_token_revoked,
)
from .auth_service import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
)

logger = logging.getLogger(__name__)


async def register_user(email: str, password: str, tenant_id: str = "default") -> dict:
    """Register a new user. Raises ValueError if email already taken."""
    existing = await get_user_by_email(email)
    if existing:
        raise ValueError("Email already registered")

    loop = asyncio.get_running_loop()
    password_hash = await loop.run_in_executor(None, hash_password, password)
    user_id = await create_user(email=email, password_hash=password_hash, tenant_id=tenant_id)
    return {"user_id": user_id, "email": email, "tenant_id": tenant_id}


async def authenticate(email: str, password: str) -> dict:
    """Verify credentials and return tokens. Raises PermissionError on failure."""
    user = await get_user_by_email(email)
    loop = asyncio.get_running_loop()
    is_valid = user and await loop.run_in_executor(
        None, verify_password, password, user["password_hash"]
    )
    if not is_valid:
        raise PermissionError("Invalid email or password")

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
        target=email,
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


async def refresh_access(refresh_token_str: str) -> dict:
    """Issue a new access token from a valid refresh token. Raises JWTError/LookupError."""
    payload = decode_token(refresh_token_str)  # raises JWTError if invalid
    if payload.get("type") != "refresh":
        raise JWTError("Not a refresh token")

    user_id = payload.get("sub")
    if not user_id:
        raise JWTError("Invalid token")
    user = await get_user_by_id(user_id)
    if not user:
        raise LookupError("User not found")

    access_token = create_access_token(
        user_id=user["id"],
        tenant_id=user["tenant_id"],
        role=user["role"],
    )
    return {"access_token": access_token, "token_type": "bearer"}


async def logout_token(token: str) -> None:
    """Revoke access token (best-effort; expired tokens are silently ignored)."""
    try:
        payload = decode_token(token)
    except JWTError:
        return  # already expired — treat as success
    jti = payload.get("jti")
    exp = payload.get("exp")
    if jti and exp:
        expires_at = datetime.fromtimestamp(exp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        await revoke_token(jti, expires_at)


async def get_authenticated_user(token: str) -> dict:
    """Validate Bearer token and return user dict. Raises PermissionError on any failure."""
    try:
        payload = decode_token(token)
    except JWTError:
        raise PermissionError("Invalid or expired token")
    if payload.get("type") != "access":
        raise PermissionError("Not an access token")
    jti = payload.get("jti")
    if jti and await is_token_revoked(jti):
        raise PermissionError("Token has been revoked")
    user_id = payload.get("sub")
    user = await get_user_by_id(user_id)
    if not user:
        raise PermissionError("User not found")
    return user
