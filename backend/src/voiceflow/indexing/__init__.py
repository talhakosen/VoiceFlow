"""indexing — one-time setup operations for project indexing.

Scans codebases, extracts identifiers, and populates the smart dictionary.
Not called during runtime transcription — triggered manually via Settings or API.
"""

from .smart_dictionary import build_smart_dictionary
from .tech_lexicon import generate_triggers

__all__ = ["build_smart_dictionary", "generate_triggers"]
