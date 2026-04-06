"""Centralized logging setup for VoiceFlow.

Call setup_logging() once at process startup (main.py, CLI scripts, workers).
All modules obtain their logger via: logger = logging.getLogger(__name__)
"""

import logging
import logging.handlers

from .config import LOG_FILE, LOG_MAX_BYTES, LOG_BACKUP_COUNT

_FMT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
_DATE_FMT = "%Y-%m-%d %H:%M:%S"

_configured = False


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger with rotating file + stderr handlers.

    Idempotent — safe to call multiple times (only configures once).
    """
    global _configured
    if _configured:
        return
    _configured = True

    formatter = logging.Formatter(_FMT, datefmt=_DATE_FMT)

    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(file_handler)
    root.addHandler(stream_handler)

    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("multipart").setLevel(logging.WARNING)
