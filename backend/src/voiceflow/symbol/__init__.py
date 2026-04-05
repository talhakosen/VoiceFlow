"""voiceflow.symbol — Symbol indexing, injection, and lookup package.

Same-level as correction/, transcription/, audio/.
"""

from .extractor import SymbolInfo, TreeSitterExtractor
from .indexer import build_symbol_index, generate_project_notes
from .injector import inject_symbol_refs
from .lookup import lookup_symbol

__all__ = [
    "SymbolInfo",
    "TreeSitterExtractor",
    "build_symbol_index",
    "generate_project_notes",
    "inject_symbol_refs",
    "lookup_symbol",
]
