"""Engineering package: symbol extraction and git repo ingestion for developer workflows."""

import logging
import re
import subprocess
from dataclasses import dataclass, field
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


@dataclass
class IngestionResult:
    files_processed: int = 0
    chunks_added: int = 0
    files_skipped: int = 0
    errors: list[str] = field(default_factory=list)


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


def ingest_git_repo(repo_path: str, tenant_id: str = "default", retriever=None) -> IngestionResult:
    """Index a git repo into ChromaDB.

    Calls ingest_folder() for all code files, then additionally ingests:
    - README.md (if present)
    - Last 50 git commit messages (as a single text chunk)

    This is synchronous and long-running — call via run_in_executor from async routes.
    """
    from ..context.ingestion import ingest_folder, IngestResult
    from ..context.chroma_retriever import ChromaRetriever
    import hashlib

    root = Path(repo_path).expanduser().resolve()
    result = IngestionResult()

    if not root.exists() or not root.is_dir():
        result.errors.append(f"Path does not exist or is not a directory: {repo_path}")
        return result

    if retriever is None:
        retriever = ChromaRetriever(tenant_id=tenant_id)

    # 1. Ingest all supported files via existing pipeline
    folder_result: IngestResult = ingest_folder(repo_path, tenant_id=tenant_id, retriever=retriever)
    result.files_processed = folder_result.files_processed
    result.chunks_added = folder_result.chunks_added
    result.files_skipped = folder_result.files_skipped
    result.errors.extend(folder_result.errors)

    # 2. Ingest git commit log (last 50 commits)
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "log", "--oneline", "-50"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            commit_text = f"# Git commit history (last 50)\n\n{proc.stdout.strip()}"
            chunk_id = "gitlog:" + hashlib.md5(str(root).encode()).hexdigest()[:12]
            retriever.add_chunks([commit_text], [chunk_id])
            result.chunks_added += 1
            logger.info("ingest_git_repo: added git log for %s", repo_path)
        else:
            logger.debug("ingest_git_repo: git log empty or not a git repo")
    except Exception as e:
        logger.warning("ingest_git_repo: git log failed: %s", e)
        result.errors.append(f"git log: {e}")

    logger.info(
        "ingest_git_repo done: %d files, %d chunks, %d errors",
        result.files_processed, result.chunks_added, len(result.errors),
    )
    return result
