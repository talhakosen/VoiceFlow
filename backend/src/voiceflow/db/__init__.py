"""VoiceFlow DB package — public API.

All imports go through here. Internal modules are an implementation detail.
"""

from .migrations import init_db
from .transcription_storage import save_transcription, get_history, clear_history, delete_transcription_by_id
from .config_storage import get_config, set_config
from .dictionary_storage import (
    get_dictionary, add_dictionary_entry, delete_dictionary_entry,
    get_snippets, add_snippet, delete_snippet, delete_snippets_by_scope,
    load_bundle_entries, clear_bundle_entries,
    get_context_status, get_context_projects, clear_smart_dictionary,
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

__all__ = [
    # Migrations
    "init_db",
    # Transcription
    "save_transcription", "get_history", "clear_history",
    # Config
    "get_config", "set_config",
    # Dictionary
    "get_dictionary", "add_dictionary_entry", "delete_dictionary_entry",
    "get_snippets", "add_snippet", "delete_snippet", "delete_snippets_by_scope",
    "load_bundle_entries", "clear_bundle_entries",
    "get_context_status", "get_context_projects", "clear_smart_dictionary",
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
    "import_training_sentences", "get_random_unrecorded_sentence", "get_training_sentence_by_id",
    "save_training_recording", "delete_training_recording",
    "get_recordings_for_sentence", "get_recorded_sentences",
    # Symbols
    "clear_symbol_indexes", "save_symbol_batch",
    "get_symbol_index_file_paths", "get_symbols_for_matching", "get_symbols_for_notes",
    "lookup_symbol_exact", "lookup_symbol_prefix", "lookup_symbol_substring",
    "clear_symbol_index_v2",
    # Token blacklist
    "revoke_token", "is_token_revoked", "purge_expired_tokens",
]
