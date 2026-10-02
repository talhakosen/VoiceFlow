"""HTTP header / query-param parsing helpers for API routes."""


def should_save_pending_wav(training_mode: str | None) -> bool:
    """True when training mode is on: keep the audio for later labelling."""
    return training_mode == "1"
