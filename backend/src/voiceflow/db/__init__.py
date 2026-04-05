from .storage import (
    init_db, save_transcription, get_history, clear_history,
    get_dictionary, add_dictionary_entry, delete_dictionary_entry,
    get_snippets, add_snippet, delete_snippet,
    create_user, get_user_by_email, get_user_by_id,
    list_users, update_user_role, deactivate_user,
    get_tenant_stats,
    append_audit_log, get_audit_log, delete_user_data,
    save_feedback,
    import_training_sentences, get_random_unrecorded_sentence, get_training_sentence_by_id,
    save_training_recording, delete_training_recording, get_recordings_for_sentence,
    get_recorded_sentences,
    # Bundle dictionary
    load_bundle_entries, clear_bundle_entries,
    # Context / smart dictionary
    get_context_status, get_context_projects, clear_smart_dictionary,
    get_dictionary_triggers, bulk_add_smart_entries,
    # Symbol index
    clear_symbol_indexes, save_symbol_batch,
    get_symbol_index_file_paths, get_symbols_for_matching, get_symbols_for_notes,
    lookup_symbol_exact, lookup_symbol_prefix, lookup_symbol_substring,
    # Token blacklist
    revoke_token, is_token_revoked, purge_expired_tokens,
)

__all__ = [
    "init_db", "save_transcription", "get_history", "clear_history",
    "get_dictionary", "add_dictionary_entry", "delete_dictionary_entry",
    "get_snippets", "add_snippet", "delete_snippet",
    "create_user", "get_user_by_email", "get_user_by_id",
    "list_users", "update_user_role", "deactivate_user",
    "get_tenant_stats",
    "append_audit_log", "get_audit_log", "delete_user_data",
    "save_feedback",
    "import_training_sentences", "get_random_unrecorded_sentence", "get_training_sentence_by_id",
    "save_training_recording", "delete_training_recording", "get_recordings_for_sentence",
    "get_recorded_sentences",
    "load_bundle_entries", "clear_bundle_entries",
    "get_context_status", "get_context_projects", "clear_smart_dictionary",
    "get_dictionary_triggers", "bulk_add_smart_entries",
    "clear_symbol_indexes", "save_symbol_batch",
    "get_symbol_index_file_paths", "get_symbols_for_matching", "get_symbols_for_notes",
    "lookup_symbol_exact", "lookup_symbol_prefix", "lookup_symbol_substring",
    "revoke_token", "is_token_revoked", "purge_expired_tokens",
]
