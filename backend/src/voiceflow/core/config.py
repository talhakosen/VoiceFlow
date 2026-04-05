"""VoiceFlow app config — config.yaml + env var override.

Priority: env var > config.yaml > built-in default
"""

import os
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).parents[4]
_CONFIG_PATH = _REPO_ROOT / "config.yaml"

def _load() -> dict:
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH) as f:
            return yaml.safe_load(f) or {}
    return {}

_raw = _load()


def _get(section: str, key: str, default: str = "") -> str:
    """Return env var if set, else config.yaml value, else default."""
    env_key = f"{section.upper()}_{key.upper()}"
    if env_val := os.getenv(env_key):
        return env_val
    return str(_raw.get(section, {}).get(key, default))


def _resolve_path(raw: str) -> Path | None:
    if not raw:
        return None
    p = Path(raw)
    if not p.is_absolute():
        p = _REPO_ROOT / p
    return p


# ── Public API ────────────────────────────────────────────────────────────────

BACKEND_MODE:    str       = _get("backend", "mode",         "local")
DB_PATH:         Path      = _resolve_path(_get("backend", "db_path", "voiceflow.db")) or \
                             Path.home() / ".voiceflow" / "voiceflow.db"

LLM_BACKEND:     str       = _get("llm", "backend",          "mlx")
LLM_ENDPOINT:    str       = _get("llm", "endpoint",         "")
LLM_MODEL:       str       = _get("llm", "model",            "qwen2.5:7b")
LLM_ADAPTER_PATH: Path | None = _resolve_path(_get("llm", "adapter_path", ""))
LLM_ADAPTER_VERSION: str      = _get("llm", "adapter_version", "")

_whisper_model_raw = _get("whisper", "model", "mlx-community/whisper-large-v3-turbo")
_whisper_model_path = _resolve_path(_whisper_model_raw)
# Use absolute path if it resolves to an existing local dir; else keep as HF repo name
WHISPER_MODEL: str = str(_whisper_model_path) if (_whisper_model_path and _whisper_model_path.exists()) else _whisper_model_raw
WHISPER_SERVER_MODEL: str  = _get("whisper", "server_model", "large-v3")

# IT-specific fine-tuned model for engineering mode (empty = use base model)
_whisper_it_raw = _get("whisper", "it_model", "")
_whisper_it_path = _resolve_path(_whisper_it_raw) if _whisper_it_raw else None
WHISPER_IT_MODEL: str = str(_whisper_it_path) if (_whisper_it_path and _whisper_it_path.exists()) else _whisper_it_raw

JWT_ACCESS_TTL_MINUTES: int = int(_get("auth", "jwt_access_ttl_minutes", "60"))

# DB encryption key — empty = plaintext (local dev); set in .env for production
# Example: DB_ENCRYPTION_KEY=<openssl rand -hex 32>
DB_ENCRYPTION_KEY: str = os.getenv("DB_ENCRYPTION_KEY", "")

# ── Security ──────────────────────────────────────────────────────────────────

# Rate limiting: "N/period" — e.g. "60/minute", "1000/hour"
RATE_LIMIT_DEFAULT:   str = _get("security", "rate_limit_default",   "60/minute")
RATE_LIMIT_STOP:      str = _get("security", "rate_limit_stop",      "30/minute")
RATE_LIMIT_AUTH:      str = _get("security", "rate_limit_auth",      "10/minute")

# CORS: comma-separated origins; "*" = allow all (local mode default)
_cors_raw = _get("security", "cors_origins", "*")
CORS_ORIGINS: list[str] = [o.strip() for o in _cors_raw.split(",") if o.strip()]

# Log rotation
LOG_FILE:         str = _get("logging", "file",          "/tmp/voiceflow.log")
LOG_MAX_BYTES:    int = int(_get("logging", "max_bytes",  str(10 * 1024 * 1024)))  # 10 MB
LOG_BACKUP_COUNT: int = int(_get("logging", "backup_count", "5"))
