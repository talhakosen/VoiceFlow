"""FeedbackService — transcription feedback (training signal) business logic."""

import logging

from ..db import save_feedback

logger = logging.getLogger(__name__)

VALID_ACTIONS = frozenset({"approved", "edited", "dismissed"})


async def record_feedback(
    raw_whisper: str,
    model_output: str,
    user_action: str,
    tenant_id: str = "default",
    user_id: str | None = None,
    user_edit: str | None = None,
    app_context: str | None = None,
    window_title: str | None = None,
    mode: str | None = None,
    language: str | None = None,
) -> None:
    """Validate and persist a feedback signal. Raises ValueError on bad action."""
    if user_action not in VALID_ACTIONS:
        raise ValueError(f"user_action must be one of {sorted(VALID_ACTIONS)}")
    await save_feedback(
        raw_whisper=raw_whisper,
        model_output=model_output,
        user_action=user_action,
        tenant_id=tenant_id,
        user_id=user_id,
        user_edit=user_edit,
        app_context=app_context,
        window_title=window_title,
        mode=mode,
        language=language,
    )
