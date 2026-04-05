"""JWT auth service — password hashing, token creation/decoding, role guards."""

import logging
import os
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, Request
from jose import JWTError, jwt  # noqa: F401 (re-exported for callers)

from ..core.config import JWT_ACCESS_TTL_MINUTES as ACCESS_TOKEN_EXPIRE_MINUTES
from ..core.config import BACKEND_MODE as _BACKEND_MODE

logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("JWT_SECRET", "voiceflow-dev-secret-change-in-prod")
ALGORITHM = "HS256"

if _BACKEND_MODE == "server" and SECRET_KEY == "voiceflow-dev-secret-change-in-prod":
    import logging as _logging
    _logging.getLogger(__name__).warning("JWT_SECRET not set in server mode — using insecure default. Set JWT_SECRET in production.")
REFRESH_TOKEN_EXPIRE_DAYS = 7


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_access_token(user_id: str, tenant_id: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "type": "access",
        "exp": expire,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": expire,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT. Raises JWTError if invalid or expired."""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


_ROLE_ORDER: dict[str, int] = {"member": 0, "admin": 1, "superadmin": 2}


def require_role(min_role: str):
    """FastAPI dependency factory. min_role: 'admin' or 'superadmin'."""

    async def _check(request: Request) -> None:
        role = getattr(request.state, "role", "member")
        if _ROLE_ORDER.get(role, 0) < _ROLE_ORDER.get(min_role, 99):
            raise HTTPException(status_code=403, detail="Insufficient role")

    return Depends(_check)
