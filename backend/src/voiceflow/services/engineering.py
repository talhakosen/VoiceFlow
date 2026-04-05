"""Engineering package: symbol extraction for developer workflows."""

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Regex patterns per language
_SYMBOL_PATTERNS = [
    # Python: class Foo, def foo_bar
    re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)"),
    re.compile(r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)"),
    # Swift / Go / TS: func fooBar, interface Foo, struct Foo
    re.compile(r"^\s*func\s+([A-Za-z_][A-Za-z0-9_]*)"),
    re.compile(r"^\s*interface\s+([A-Za-z_][A-Za-z0-9_]*)"),
    re.compile(r"^\s*struct\s+([A-Za-z_][A-Za-z0-9_]*)"),
    # TypeScript / JS: const FOO / const fooBar
    re.compile(r"^\s*(?:export\s+)?const\s+([A-Za-z_][A-Za-z0-9_]*)"),
    # Go: type Foo struct|interface
    re.compile(r"^\s*type\s+([A-Za-z_][A-Za-z0-9_]*)\s+(?:struct|interface)"),
]

_CODE_EXTENSIONS = {".py", ".swift", ".ts", ".tsx", ".js", ".go"}
_MAX_FILE_SIZE = 512 * 1024  # 512 KB


def extract_symbols(repo_path: str) -> list[str]:
    """Extract class/function/variable names from code files in a git repo.

    Scans Python, Swift, TypeScript, Go files using regex.
    Returns a deduplicated, sorted list of symbol names.
    """
    root = Path(repo_path).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        logger.warning("extract_symbols: path not found: %s", repo_path)
        return []

    symbols: set[str] = set()

    for file_path in root.rglob("*"):
        # Skip hidden, __pycache__, node_modules, .git
        parts = file_path.parts
        if any(
            p.startswith(".") or p in {"__pycache__", "node_modules", "dist", "build"}
            for p in parts
        ):
            continue
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in _CODE_EXTENSIONS:
            continue
        if file_path.stat().st_size > _MAX_FILE_SIZE:
            continue

        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            for line in text.splitlines():
                for pattern in _SYMBOL_PATTERNS:
                    m = pattern.match(line)
                    if m:
                        name = m.group(1)
                        # Filter out single-char and very generic names
                        if len(name) > 1:
                            symbols.add(name)
                        break
        except Exception as e:
            logger.debug("extract_symbols: skip %s: %s", file_path.name, e)

    result = sorted(symbols)
    logger.info("extract_symbols: found %d symbols in %s", len(result), repo_path)
    return result
