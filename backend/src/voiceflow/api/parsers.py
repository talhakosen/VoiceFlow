"""HTTP header / query-param parsing helpers for API routes."""


def parse_cmd_intervals(raw: str | None) -> list[tuple[float, float]] | None:
    """Parse 'X-Cmd-Intervals' header: '1.10-2.30,4.50-5.10' → [(1.10, 2.30), …]."""
    if not raw:
        return None
    try:
        return [
            (float(a), float(b))
            for part in raw.split(",")
            for a, b in [part.strip().split("-", 1)]
        ]
    except Exception:
        return None


def parse_it_dataset_index(raw: str | None) -> int | None:
    """Parse 'X-IT-Dataset-Index' header string to int, or None on failure."""
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def should_save_pending_wav(training_mode: str | None, it_dataset_index: int | None) -> bool:
    """Return True if this stop should save a pending WAV for later labelling."""
    return training_mode == "1" and it_dataset_index is None
