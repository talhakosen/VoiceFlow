#!/usr/bin/env python3
"""Migrate existing plaintext voiceflow.db → SQLCipher encrypted DB.

Usage:
    DB_ENCRYPTION_KEY=<your-key> python scripts/migrate_db_encrypt.py

The script:
1. Opens the existing plaintext DB
2. Creates a temp encrypted copy
3. Verifies the encrypted copy is readable
4. Replaces the original with the encrypted copy

BACKUP THE ORIGINAL FIRST — this script overwrites it.
"""

import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

# Repo root → config.yaml path resolution
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from voiceflow.core.config import DB_PATH, DB_ENCRYPTION_KEY

if not DB_ENCRYPTION_KEY:
    print("ERROR: DB_ENCRYPTION_KEY env var is not set.")
    print("Generate one: openssl rand -hex 32")
    sys.exit(1)

if not DB_PATH.exists():
    print(f"ERROR: DB not found: {DB_PATH}")
    sys.exit(1)


def is_encrypted(path: Path) -> bool:
    """Return True if DB is already SQLCipher encrypted."""
    try:
        conn = sqlite3.connect(str(path))
        conn.execute("SELECT count(*) FROM sqlite_master")
        conn.close()
        return False
    except sqlite3.DatabaseError:
        return True


if is_encrypted(DB_PATH):
    print(f"DB is already encrypted: {DB_PATH}")
    sys.exit(0)

print(f"Source (plaintext): {DB_PATH}")

# Backup
backup = DB_PATH.with_suffix(".db.plaintext.bak")
shutil.copy2(DB_PATH, backup)
print(f"Backup created: {backup}")

# Use SQLCipher's built-in sqlcipher_export to encrypt in-place
import sqlcipher3

tmp_fd, tmp_path = tempfile.mkstemp(suffix=".db")
os.close(tmp_fd)
tmp_path = Path(tmp_path)
tmp_path.unlink()

src = sqlcipher3.connect(str(DB_PATH))
# Attach & export to encrypted file
src.execute(f"ATTACH DATABASE '{tmp_path}' AS encrypted KEY '{DB_ENCRYPTION_KEY}'")
src.execute("SELECT sqlcipher_export('encrypted')")
src.execute("DETACH DATABASE encrypted")
src.close()

# Verify
test = sqlcipher3.connect(str(tmp_path))
test.execute(f"PRAGMA key='{DB_ENCRYPTION_KEY}'")
count = test.execute("SELECT count(*) FROM sqlite_master").fetchone()[0]
test.close()
print(f"Encrypted DB verified: {count} tables")

# Replace original
shutil.move(str(tmp_path), str(DB_PATH))
print(f"Done: {DB_PATH} is now encrypted.")
print(f"Keep backup safe: {backup}")
