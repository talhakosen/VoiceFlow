"""Unit tests for POST /api/feedback endpoint and save_feedback storage."""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Storage layer
# ---------------------------------------------------------------------------

def test_save_feedback_returns_id():
    """save_feedback() must return a positive integer row id."""
    from voiceflow.db.storage import save_feedback

    async def _run():
        with patch("voiceflow.db.storage.aiosqlite.connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_conn.__aexit__ = AsyncMock(return_value=False)
            mock_cursor = MagicMock()
            mock_cursor.lastrowid = 42
            mock_conn.execute = AsyncMock(return_value=mock_cursor)
            mock_conn.commit = AsyncMock()
            mock_connect.return_value = mock_conn

            result = await save_feedback(
                raw_whisper="merhaba dunya",
                model_output="Merhaba dünya.",
                user_action="approved",
            )
            return result

    result = asyncio.run(_run())
    assert result == 42


def test_save_feedback_edited_action():
    """save_feedback() with 'edited' action and user_edit must not raise."""
    from voiceflow.db.storage import save_feedback

    async def _run():
        with patch("voiceflow.db.storage.aiosqlite.connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_conn.__aexit__ = AsyncMock(return_value=False)
            mock_cursor = MagicMock()
            mock_cursor.lastrowid = 7
            mock_conn.execute = AsyncMock(return_value=mock_cursor)
            mock_conn.commit = AsyncMock()
            mock_connect.return_value = mock_conn

            result = await save_feedback(
                raw_whisper="merhaba dunya",
                model_output="Merhaba dünya.",
                user_action="edited",
                user_edit="Merhaba, Dünya!",
                mode="general",
                language="tr",
            )
            return result

    result = asyncio.run(_run())
    assert result == 7


# ---------------------------------------------------------------------------
# API endpoint
# ---------------------------------------------------------------------------

def _make_app():
    """Create a minimal FastAPI app with the router mounted (no RecordingService needed for feedback)."""
    import os
    os.environ.setdefault("BACKEND_MODE", "local")
    from fastapi import FastAPI
    from voiceflow.api.routes import router
    from voiceflow.api.auth import verify_api_key
    from fastapi import Request

    app = FastAPI()

    # Override auth dependency to always pass
    async def _no_auth():
        pass

    app.dependency_overrides[verify_api_key] = _no_auth

    # Provide a dummy recording service on app.state so other endpoints don't break
    app.state.recording_service = MagicMock()

    app.include_router(router, prefix="/api")
    return app


def test_feedback_endpoint_approved():
    """POST /api/feedback with approved action must return 200 {"status": "ok"}."""
    app = _make_app()
    client = TestClient(app)

    with patch("voiceflow.api.routes.save_feedback", new_callable=AsyncMock, return_value=1) as mock_save:
        resp = client.post("/api/feedback", json={
            "raw_whisper": "merhaba dunya",
            "model_output": "Merhaba dünya.",
            "user_action": "approved",
        })

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    mock_save.assert_called_once()


def test_feedback_endpoint_edited():
    """POST /api/feedback with edited action and user_edit must return 200."""
    app = _make_app()
    client = TestClient(app)

    with patch("voiceflow.api.routes.save_feedback", new_callable=AsyncMock, return_value=2):
        resp = client.post("/api/feedback", json={
            "raw_whisper": "merhaba dunya",
            "model_output": "Merhaba dünya.",
            "user_action": "edited",
            "user_edit": "Merhaba, Dünya!",
            "mode": "general",
            "language": "tr",
        })

    assert resp.status_code == 200


def test_feedback_endpoint_dismissed():
    """POST /api/feedback with dismissed action must return 200."""
    app = _make_app()
    client = TestClient(app)

    with patch("voiceflow.api.routes.save_feedback", new_callable=AsyncMock, return_value=3):
        resp = client.post("/api/feedback", json={
            "raw_whisper": "merhaba dunya",
            "model_output": "Merhaba dünya.",
            "user_action": "dismissed",
        })

    assert resp.status_code == 200


def test_feedback_endpoint_invalid_action():
    """POST /api/feedback with unknown user_action must return 400."""
    app = _make_app()
    client = TestClient(app)

    with patch("voiceflow.api.routes.save_feedback", new_callable=AsyncMock):
        resp = client.post("/api/feedback", json={
            "raw_whisper": "merhaba",
            "model_output": "Merhaba.",
            "user_action": "unknown_action",
        })

    assert resp.status_code == 400


def test_feedback_endpoint_missing_required_fields():
    """POST /api/feedback without required fields must return 422."""
    app = _make_app()
    client = TestClient(app)

    resp = client.post("/api/feedback", json={"user_action": "approved"})
    assert resp.status_code == 422
