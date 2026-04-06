"""Transcription history storage."""

import json

from ._base import aiosqlite, DB_PATH


async def save_transcription(
    text: str,
    raw_text: str | None = None,
    corrected: bool = False,
    language: str | None = None,
    duration: float | None = None,
    mode: str = "general",
    user_id: str | None = None,
    tenant_id: str = "default",
    processing_ms: int | None = None,
    whisper_model: str | None = None,
    corrections: dict | None = None,
) -> int | None:
    """Save a transcription to history. Returns the new row id.

    `corrections` JSON structure (all keys optional):
    {
      "dict":    {"original_token": "replacement", ...},
      "snippet": {"trigger_phrase": "expansion"},
      "symbol":  {"symbol_name": "file.swift:42"},
      "llm":     {"in": "text before LLM", "out": "text after LLM"}
    }
    """
    corrections_json = json.dumps(corrections, ensure_ascii=False) if corrections else None
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO transcriptions (text, raw_text, corrected, language, duration, mode, user_id, tenant_id, processing_ms, whisper_model, corrections) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (text, raw_text, int(corrected), language, duration, mode, user_id, tenant_id, processing_ms, whisper_model, corrections_json),
        )
        await db.commit()
        return cursor.lastrowid


async def get_history(
    limit: int = 100,
    offset: int = 0,
    user_id: str | None = None,
    tenant_id: str = "default",
) -> list[dict]:
    """Return transcription history for a tenant, newest first."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if user_id:
            query = "SELECT * FROM transcriptions WHERE tenant_id = ? AND user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params = (tenant_id, user_id, limit, offset)
        else:
            query = "SELECT * FROM transcriptions WHERE tenant_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params = (tenant_id, limit, offset)
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def clear_history(tenant_id: str = "default") -> None:
    """Delete transcription history for a tenant."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM transcriptions WHERE tenant_id = ?", (tenant_id,))
        await db.commit()
