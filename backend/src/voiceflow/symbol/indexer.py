"""symbol/indexer.py — Build symbol index from code files.

Scans a project folder with tree-sitter, writes to symbol_index_v2 (rich)
and symbol_index (backward compat flat). Also generates project-notes.md.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

import aiosqlite

from ..core.config import DB_PATH
from .extractor import SymbolInfo, _LANGUAGE_MAP, _MAX_FILE_BYTES, _extractor

logger = logging.getLogger(__name__)

_SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", "build", "dist",
              "DerivedData", ".build", "Pods", "vendor", ".claude", "worktrees"}


async def build_symbol_index(folder_path: str, user_id: str) -> int:
    """Scan folder with tree-sitter, write to symbol_index_v2 + symbol_index (compat)."""
    root = Path(folder_path).expanduser().resolve()
    if not root.exists():
        return 0

    logger.info("Symbol index: scanning %s for user %s", root, user_id)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM symbol_index_v2 WHERE user_id = ? AND project_path = ?",
            (user_id, str(root)),
        )
        await db.execute(
            "DELETE FROM symbol_index WHERE user_id = ? AND project_path = ?",
            (user_id, str(root)),
        )
        await db.commit()

    all_symbols: list[SymbolInfo] = []

    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue
        if any(part in _SKIP_DIRS for part in file_path.parts):
            continue
        if file_path.suffix.lower() not in _LANGUAGE_MAP:
            continue
        if file_path.stat().st_size > _MAX_FILE_BYTES:
            continue

        symbols = _extractor.extract(file_path, root)
        all_symbols.extend(symbols)

    if not all_symbols:
        return 0

    async with aiosqlite.connect(DB_PATH) as db:
        for sym in all_symbols:
            await db.execute(
                """INSERT INTO symbol_index_v2
                   (user_id, project_path, file_path, symbol_type, symbol_name,
                    line_number, end_line, signature, parent_symbol, parent_class,
                    conformances, return_type, properties, imports, decorators,
                    visibility, is_static)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    user_id, str(root), sym.file_path, sym.symbol_type, sym.symbol_name,
                    sym.line_number, sym.end_line, sym.signature, sym.parent_symbol,
                    sym.parent_class, sym.conformances, sym.return_type,
                    json.dumps(sym.properties, ensure_ascii=False) if sym.properties else None,
                    json.dumps(sym.imports, ensure_ascii=False) if sym.imports else None,
                    json.dumps(sym.decorators, ensure_ascii=False) if sym.decorators else None,
                    sym.visibility, int(sym.is_static),
                ),
            )
            await db.execute(
                """INSERT OR IGNORE INTO symbol_index
                   (user_id, project_path, file_path, symbol_type, symbol_name, line_number)
                   VALUES (?,?,?,?,?,?)""",
                (user_id, str(root), sym.file_path, sym.symbol_type, sym.symbol_name, sym.line_number),
            )
        await db.commit()

    logger.info("symbol_index_v2: %d symbols indexed from %s", len(all_symbols), root)
    return len(all_symbols)


async def generate_project_notes(folder_path: str, user_id: str) -> str:
    """Generate .claude/project-notes.md from symbol_index_v2."""
    root = Path(folder_path).expanduser().resolve()

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT symbol_type, symbol_name, file_path, line_number,
                      parent_class, conformances, signature, imports
               FROM symbol_index_v2
               WHERE user_id = ? AND project_path = ?
               ORDER BY symbol_type, symbol_name""",
            (user_id, str(root)),
        )
        rows = [dict(r) for r in await cur.fetchall()]

    if not rows:
        return ""

    by_type: dict[str, list] = {}
    for r in rows:
        by_type.setdefault(r["symbol_type"], []).append(r)

    lang_counts: dict[str, int] = {}
    for r in rows:
        ext = Path(r["file_path"]).suffix.lower()
        lang = _LANGUAGE_MAP.get(ext, ext)
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
    lang_str = ", ".join(f"{lang} ({cnt})" for lang, cnt in sorted(lang_counts.items()))

    patterns = []
    classes = by_type.get("class", []) + by_type.get("struct", [])
    class_names = [c["symbol_name"] for c in classes]
    if any(n.endswith("Repository") for n in class_names):
        patterns.append("Repository Pattern")
    if any(n.endswith("Service") for n in class_names):
        patterns.append("Service Layer")
    if any(n.endswith("ViewModel") for n in class_names):
        patterns.append("MVVM")
    if any(n.startswith("Abstract") or n.endswith("Protocol") for n in class_names):
        patterns.append("Dependency Injection (Protocol/Abstract)")
    if any(n.endswith("Factory") for n in class_names):
        patterns.append("Factory Pattern")

    all_imports: set[str] = set()
    _noise = {"re", "os", "sys", "io", "abc", "json", "time", "math", "copy",
              "typing", "types", "enum", "uuid", "datetime", "pathlib", "logging",
              "functools", "itertools", "collections", "dataclasses", "contextlib",
              "asyncio", "inspect", "hashlib", "struct", "base64", "threading",
              "gc", "queue", "concurrent", "subprocess", "socket", "signal",
              "traceback", "warnings", "weakref", "shutil", "tempfile", "glob",
              "api", "audio", "auth", "core", "db", "services", "transcription",
              "correction", "context"}
    for r in rows:
        if r["imports"]:
            try:
                imps = json.loads(r["imports"])
                for imp in imps:
                    mod = imp.strip().split(".")[0]
                    if (mod and len(mod) > 1 and not mod.startswith("_")
                            and mod not in _noise and mod[0].isalpha()):
                        all_imports.add(mod)
            except Exception:
                pass

    lines = [
        f"# Project Context -- {root.name}",
        f"> Auto-generated by VoiceFlow. Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Architecture Overview",
        f"- **Symbols:** {len(rows)} total ({', '.join(f'{t}: {len(v)}' for t, v in sorted(by_type.items()))})",
        f"- **Languages:** {lang_str}",
        "",
    ]

    if patterns:
        lines += ["## Patterns Detected", ""]
        for p in patterns:
            lines.append(f"- {p}")
        lines.append("")

    if all_imports:
        lines += ["## Key Libraries & Imports", ""]
        lines.append(", ".join(sorted(all_imports)[:30]))
        lines.append("")

    key_symbols = [r for r in (by_type.get("class", []) + by_type.get("struct", []) +
                               by_type.get("protocol", []) + by_type.get("interface", []))
                   if r.get("parent_class") or r.get("conformances")][:40]

    if key_symbols:
        lines += ["## Key Symbols", "",
                   "| Name | Type | File:Line | Inherits | Conforms To |",
                   "|------|------|-----------|----------|-------------|"]
        for r in key_symbols:
            lines.append(
                f"| {r['symbol_name']} | {r['symbol_type']} | {r['file_path']}:{r['line_number']} "
                f"| {r.get('parent_class') or '-'} | {r.get('conformances') or '-'} |"
            )
        lines.append("")

    repos_services = [r for r in by_type.get("class", [])
                      if r["symbol_name"].endswith(("Repository", "Service", "Manager", "Controller"))][:20]
    if repos_services:
        lines += ["## Repositories & Services", ""]
        for r in repos_services:
            lines.append(f"### {r['symbol_name']}")
            lines.append(f"- **File:** `{r['file_path']}:{r['line_number']}`")
            if r.get("parent_class"):
                lines.append(f"- **Extends:** {r['parent_class']}")
            if r.get("conformances"):
                lines.append(f"- **Implements:** {r['conformances']}")
            lines.append("")

    content = "\n".join(lines)

    notes_path = root / ".claude" / "project-notes.md"
    notes_path.parent.mkdir(parents=True, exist_ok=True)
    notes_path.write_text(content, encoding="utf-8")
    logger.info("project-notes.md written: %s (%d bytes)", notes_path, len(content))
    return str(notes_path)
