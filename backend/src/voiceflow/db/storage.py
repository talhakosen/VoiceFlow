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
    get_snippets, add_snippet, delete_snippet, delete_snippets_by_scope,
    load_bundle_entries, clear_bundle_entries,
    get_context_status, get_context_projects, clear_smart_dictionary,
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
from .training_storage import (
    import_training_sentences, get_random_unrecorded_sentence, get_training_sentence_by_id,
    save_training_recording, delete_training_recording,
    get_recordings_for_sentence, get_recorded_sentences,
)
from .symbol_storage import (
    clear_symbol_indexes, save_symbol_batch,
    get_symbol_index_file_paths, get_symbols_for_matching, get_symbols_for_notes,
    lookup_symbol_exact, lookup_symbol_prefix, lookup_symbol_substring,
    clear_symbol_index_v2,
)
from .token_storage import revoke_token, is_token_revoked, purge_expired_tokens
from ._base import aiosqlite, DB_PATH

__all__ = [
    "init_db",
    "save_transcription", "get_history", "clear_history",
    "get_config", "set_config",
    "get_dictionary", "add_dictionary_entry", "delete_dictionary_entry",
    "get_snippets", "add_snippet", "delete_snippet", "delete_snippets_by_scope",
    "load_bundle_entries", "clear_bundle_entries",
    "get_context_status", "get_context_projects", "clear_smart_dictionary",
    "get_dictionary_triggers", "bulk_add_smart_entries",
    "create_user", "get_user_by_email", "get_user_by_id",
    "list_users", "update_user_role", "deactivate_user",
    "append_audit_log", "get_audit_log",
    "save_feedback", "get_tenant_stats", "delete_user_data",
    "import_training_sentences", "get_random_unrecorded_sentence", "get_training_sentence_by_id",
    "save_training_recording", "delete_training_recording",
    "get_recordings_for_sentence", "get_recorded_sentences",
    "clear_symbol_indexes", "save_symbol_batch",
    "get_symbol_index_file_paths", "get_symbols_for_matching", "get_symbols_for_notes",
    "lookup_symbol_exact", "lookup_symbol_prefix", "lookup_symbol_substring",
    "clear_symbol_index_v2",
    "revoke_token", "is_token_revoked", "purge_expired_tokens",
    "aiosqlite", "DB_PATH",
]
