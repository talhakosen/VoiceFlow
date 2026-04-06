"""Shared DB connection infrastructure."""

import sqlite3

from .cipher_connection import connect as _sqlcipher_connect
from ..core.config import DB_PATH


class _AiosqliteCompat:
    """Drop-in shim: `aiosqlite.connect(path)` → cipher_connection.connect(path)."""

    Row = sqlite3.Row  # used as db.row_factory = aiosqlite.Row

    def connect(self, path):
        return _sqlcipher_connect(path)


aiosqlite = _AiosqliteCompat()

__all__ = ["aiosqlite", "DB_PATH"]
