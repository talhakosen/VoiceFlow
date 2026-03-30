"""Snippets post-processing — exact-match expansion pass.

Applied after dictionary substitution, before LLM correction.
Replaces the entire transcript if it exactly matches a trigger phrase.
"""


def apply_snippets(text: str, snippets: list[dict]) -> str:
    """Expand text if it exactly matches a snippet trigger phrase.

    - Exact match first (original casing)
    - Fallback: stripped + lowercased match
    - Returns expansion if matched, original text otherwise
    - Short-circuits if snippets list is empty
    """
    if not snippets:
        return text

    stripped = text.strip()
    stripped_lower = stripped.lower()

    for snippet in snippets:
        trigger = snippet.get("trigger_phrase", "").strip()
        expansion = snippet.get("expansion", "").strip()
        if not trigger or not expansion:
            continue
        # Exact match
        if stripped == trigger:
            return expansion
        # Case-insensitive match
        if stripped_lower == trigger.lower():
            return expansion

    return text
