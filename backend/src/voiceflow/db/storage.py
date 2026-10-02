"""Backward-compatibility shim.

All functions have been moved to dedicated submodules.
Import from `voiceflow.db` (the package) instead.

This file exists only for legacy `from ..db.storage import X` imports.
"""

from .migrations import init_db
from .transcription_storage import save_transcription, get_history, clear_history
from .config_storage import get_config, set_config
from .dictionary_storage import (
    get_dictionary, add_dictionary_entry, delete_dictionary_entry,
    load_bundle_entries, clear_bundle_entries,
    get_context_status, clear_smart_dictionary,
    get_dictionary_triggers, bulk_add_smart_entries,
)
from .user_storage import (
    create_user, get_user_by_email, get_user_by_id,
    list_users, update_user_role, deactivate_user,
)
from .audit_storage import (
    append_audit_log, get_audit_log,
    save_feedback, get_tenant_stats, delete_user_data,
)
from .token_storage import revoke_token, is_token_revoked, purge_expired_tokens
from ._base import aiosqlite, DB_PATH

__all__ = [
    "init_db",
    "save_transcription", "get_history", "clear_history",
    "get_config", "set_config",
    "get_dictionary", "add_dictionary_entry", "delete_dictionary_entry",
    "load_bundle_entries", "clear_bundle_entries",
    "get_context_status", "clear_smart_dictionary",
    "get_dictionary_triggers", "bulk_add_smart_entries",
    "create_user", "get_user_by_email", "get_user_by_id",
    "list_users", "update_user_role", "deactivate_user",
    "append_audit_log", "get_audit_log",
    "save_feedback", "get_tenant_stats", "delete_user_data",
    "revoke_token", "is_token_revoked", "purge_expired_tokens",
    "aiosqlite", "DB_PATH",
]
