"""VoiceFlow DB package — public API.

All imports go through here. Internal modules are an implementation detail.
"""

from .migrations import init_db
from .transcription_storage import save_transcription, get_history, clear_history, delete_transcription_by_id
from .config_storage import get_config, set_config
from .dictionary_storage import (
    get_dictionary, add_dictionary_entry, delete_dictionary_entry,
    load_bundle_entries, clear_bundle_entries,
    get_context_status, clear_smart_dictionary,
    get_dictionary_triggers, bulk_add_smart_entries,
    dictionary_version, invalidate_dictionary_cache,
    warm_dictionary_cache, last_active_user_id,
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

__all__ = [
    # Migrations
    "init_db",
    # Transcription
    "save_transcription", "get_history", "clear_history",
    # Config
    "get_config", "set_config",
    # Dictionary
    "get_dictionary", "add_dictionary_entry", "delete_dictionary_entry",
    "load_bundle_entries", "clear_bundle_entries",
    "get_context_status", "clear_smart_dictionary",
    "get_dictionary_triggers", "bulk_add_smart_entries",
    "dictionary_version", "invalidate_dictionary_cache",
    "warm_dictionary_cache", "last_active_user_id",
    # Users
    "create_user", "get_user_by_email", "get_user_by_id",
    "list_users", "update_user_role", "deactivate_user",
    # Audit / Feedback / Stats
    "append_audit_log", "get_audit_log",
    "save_feedback", "get_tenant_stats", "delete_user_data",
    # Training
    # Symbols
    # Token blacklist
    "revoke_token", "is_token_revoked", "purge_expired_tokens",
]
