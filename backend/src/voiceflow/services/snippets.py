"""Snippets post-processing — exact-match expansion pass.

Applied after dictionary substitution, before LLM correction.
Replaces the entire transcript if it exactly matches a trigger phrase.
"""


def apply_snippets(text: str, snippets: list[dict]) -> tuple[str, dict[str, str] | None]:
    """Expand text if it exactly matches a snippet trigger phrase.

    - Exact match first (original casing)
    - Fallback: stripped + lowercased match
    - Returns (expansion, {trigger: expansion}) if matched
    - Returns (original_text, None) otherwise
    """
    if not snippets:
        return text, None

    stripped = text.strip().rstrip(".,!?;:")
    stripped_lower = stripped.lower()

    for snippet in snippets:
        trigger = snippet.get("trigger_phrase", "").strip()
        expansion = snippet.get("expansion", "").strip()
        if not trigger or not expansion:
            continue
        # Exact match
        if stripped == trigger:
            return expansion, {trigger: expansion}
        # Case-insensitive match
        if stripped_lower == trigger.lower():
            return expansion, {trigger: expansion}

    return text, None
