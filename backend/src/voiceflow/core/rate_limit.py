"""Shared slowapi rate limiter instance."""

from slowapi import Limiter
from slowapi.util import get_remote_address

from .config import RATE_LIMIT_DEFAULT, RATE_LIMIT_STOP, RATE_LIMIT_AUTH

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[RATE_LIMIT_DEFAULT],
)

__all__ = ["limiter", "RATE_LIMIT_STOP", "RATE_LIMIT_AUTH"]
