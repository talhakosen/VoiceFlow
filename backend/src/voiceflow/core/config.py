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

_whisper_model_raw = _get("whisper", "model", "mlx-community/whisper-large-v3-turbo")
_whisper_model_path = _resolve_path(_whisper_model_raw)
# Use absolute path if it resolves to an existing local dir; else keep as HF repo name
WHISPER_MODEL: str = str(_whisper_model_path) if (_whisper_model_path and _whisper_model_path.exists()) else _whisper_model_raw
WHISPER_SERVER_MODEL: str  = _get("whisper", "server_model", "large-v3")

JWT_ACCESS_TTL_MINUTES: int = int(_get("auth", "jwt_access_ttl_minutes", "60"))
