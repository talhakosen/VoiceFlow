"""symbol_indexer.py — Kod tabanından class/struct/func/enum sembollerini çıkar.

Desteklenen diller: Swift, Dart, Python, TypeScript/JavaScript, Go, Kotlin

Her sembol için: file_path + symbol_name + symbol_type + line_number
"""

import re
import logging
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

DB_PATH = Path.home() / ".voiceflow" / "voiceflow.db"

# Her dil için (symbol_type, regex) çiftleri
_EXTRACTORS: dict[str, list[tuple[str, re.Pattern]]] = {
    ".swift": [
        ("class",    re.compile(r'^\s*(?:public |private |internal |open |final )*class\s+(\w+)', re.M)),
        ("struct",   re.compile(r'^\s*(?:public |private |internal )*struct\s+(\w+)', re.M)),
        ("enum",     re.compile(r'^\s*(?:public |private |internal )*enum\s+(\w+)', re.M)),
        ("protocol", re.compile(r'^\s*(?:public |private |internal )*protocol\s+(\w+)', re.M)),
        ("func",     re.compile(r'^\s*(?:public |private |internal |override |static |class )*func\s+(\w+)', re.M)),
    ],
    ".dart": [
        ("class",    re.compile(r'^\s*(?:abstract\s+)?class\s+(\w+)', re.M)),
        ("mixin",    re.compile(r'^\s*mixin\s+(\w+)', re.M)),
        ("enum",     re.compile(r'^\s*enum\s+(\w+)', re.M)),
        ("func",     re.compile(r'^\s+(?:Future<\S+>|void|String|int|bool|List|Map|\w+)\s+(\w+)\s*\(', re.M)),
    ],
    ".py": [
        ("class",    re.compile(r'^class\s+(\w+)', re.M)),
        ("func",     re.compile(r'^def\s+(\w+)', re.M)),
        ("func",     re.compile(r'^    def\s+(\w+)', re.M)),
    ],
    ".ts": [
        ("class",    re.compile(r'^\s*(?:export\s+)?(?:abstract\s+)?class\s+(\w+)', re.M)),
        ("interface",re.compile(r'^\s*(?:export\s+)?interface\s+(\w+)', re.M)),
        ("enum",     re.compile(r'^\s*(?:export\s+)?enum\s+(\w+)', re.M)),
        ("func",     re.compile(r'^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)', re.M)),
    ],
    ".kt": [
        ("class",    re.compile(r'^\s*(?:data\s+|sealed\s+|abstract\s+|open\s+)?class\s+(\w+)', re.M)),
        ("object",   re.compile(r'^\s*object\s+(\w+)', re.M)),
        ("func",     re.compile(r'^\s*(?:suspend\s+)?fun\s+(\w+)', re.M)),
    ],
    ".go": [
        ("struct",   re.compile(r'^type\s+(\w+)\s+struct', re.M)),
        ("interface",re.compile(r'^type\s+(\w+)\s+interface', re.M)),
        ("func",     re.compile(r'^func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)', re.M)),
    ],
}
_SUPPORTED = set(_EXTRACTORS.keys())
_MAX_FILE_SIZE = 500_000


def _extract_symbols(file_path: Path, project_root: Path) -> list[dict]:
    """Dosyadan sembol listesi çıkar. [{file_path, symbol_type, symbol_name, line_number}]"""
    ext = file_path.suffix.lower()
    extractors = _EXTRACTORS.get(ext)
    if not extractors:
        return []

    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    # Satır numarası hesaplamak için satır başlangıç offset'leri
    line_starts = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            line_starts.append(i + 1)

    def offset_to_line(offset: int) -> int:
        lo, hi = 0, len(line_starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if line_starts[mid] <= offset:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1  # 1-indexed

    rel_path = str(file_path.relative_to(project_root))
    results = []

    for symbol_type, pattern in extractors:
        for match in pattern.finditer(text):
            name = match.group(1)
            if len(name) < 2:
                continue
            line = offset_to_line(match.start())
            results.append({
                "file_path": rel_path,
                "symbol_type": symbol_type,
                "symbol_name": name,
                "line_number": line,
            })

    return results


async def build_symbol_index(folder_path: str, user_id: str) -> int:
    """Klasörü tara, sembolleri symbol_index tablosuna yaz.

    Mevcut user_id entries önce silinir (tam yeniden index).
    Returns: eklenen sembol sayısı
    """
    root = Path(folder_path).expanduser().resolve()
    if not root.exists():
        return 0

    logger.info("Symbol index: scanning %s for user %s", root, user_id)

    all_symbols: list[dict] = []
    for file_path in root.rglob("*"):
        if any(p.startswith(".") or p in ("__pycache__", "node_modules", "build", ".build", "DerivedData")
               for p in file_path.parts):
            continue
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in _SUPPORTED:
            continue
        if file_path.stat().st_size > _MAX_FILE_SIZE:
            continue
        symbols = _extract_symbols(file_path, root)
        all_symbols.extend(symbols)

    logger.info("Symbol index: found %d symbols", len(all_symbols))
    if not all_symbols:
        return 0

    added = 0
    async with aiosqlite.connect(DB_PATH) as db:
        # Önce bu kullanıcının index'ini temizle
        await db.execute("DELETE FROM symbol_index WHERE user_id = ? AND project_path = ?", (user_id, str(root)))

        for sym in all_symbols:
            await db.execute(
                "INSERT INTO symbol_index (user_id, project_path, file_path, symbol_type, symbol_name, line_number) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, str(root), sym["file_path"], sym["symbol_type"], sym["symbol_name"], sym["line_number"]),
            )
            added += 1

        await db.commit()

    logger.info("Symbol index: added %d symbols for user %s", added, user_id)
    return added


async def inject_symbol_refs(text: str, user_id: str) -> str:
    """Metindeki bilinen sembolleri tespit et, başa @file:line referansı ekle.

    "HistoryView buradaki metotlar" → "@VoiceFlowApp/Sources/HistoryView.swift:2 HistoryView buradaki metotlar"

    Sadece sınıf/struct/protocol seviyesindeki sembollere referans verir (func değil —
    çok fazla eşleşme olur). Birden fazla sembol bulunursa hepsi eklenir.
    """
    import re as _re

    # Büyük harfle başlayan, 4+ karakter token'ları çıkar (sembol adayları)
    candidates = _re.findall(r'\b([A-Z][a-zA-Z0-9]{3,})\b', text)
    if not candidates:
        return text

    seen = set()
    refs: list[str] = []

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        for name in dict.fromkeys(candidates):  # preserve order, deduplicate
            if name in seen:
                continue
            async with db.execute(
                """SELECT symbol_name, symbol_type, file_path, line_number
                   FROM symbol_index
                   WHERE user_id = ? AND LOWER(symbol_name) = LOWER(?)
                     AND symbol_type IN ('class','struct','protocol','enum','interface','object')
                   ORDER BY CASE symbol_type WHEN 'class' THEN 0 WHEN 'struct' THEN 1 ELSE 2 END
                   LIMIT 1""",
                (user_id, name),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    refs.append(f"@{row['file_path']}:{row['line_number']}")
                    seen.add(name)

    if not refs:
        return text

    return " ".join(refs) + " " + text


async def lookup_symbol(query: str, user_id: str, limit: int = 5) -> list[dict]:
    """Sembol adına göre fuzzy arama. En iyi eşleşmeleri döner.

    Returns: [{symbol_name, symbol_type, file_path, line_number}]
    """
    query = query.strip()
    if not query:
        return []

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Önce tam eşleşme (case-insensitive)
        async with db.execute(
            """SELECT symbol_name, symbol_type, file_path, line_number
               FROM symbol_index
               WHERE user_id = ? AND LOWER(symbol_name) = LOWER(?)
               ORDER BY CASE symbol_type WHEN 'class' THEN 0 WHEN 'struct' THEN 1 ELSE 2 END
               LIMIT ?""",
            (user_id, query, limit),
        ) as cursor:
            rows = [dict(r) for r in await cursor.fetchall()]

        if rows:
            return rows

        # Prefix eşleşme
        async with db.execute(
            """SELECT symbol_name, symbol_type, file_path, line_number
               FROM symbol_index
               WHERE user_id = ? AND LOWER(symbol_name) LIKE LOWER(?)
               ORDER BY length(symbol_name)
               LIMIT ?""",
            (user_id, f"{query}%", limit),
        ) as cursor:
            rows = [dict(r) for r in await cursor.fetchall()]

        if rows:
            return rows

        # Substring eşleşme
        async with db.execute(
            """SELECT symbol_name, symbol_type, file_path, line_number
               FROM symbol_index
               WHERE user_id = ? AND LOWER(symbol_name) LIKE LOWER(?)
               ORDER BY length(symbol_name)
               LIMIT ?""",
            (user_id, f"%{query}%", limit),
        ) as cursor:
            return [dict(r) for r in await cursor.fetchall()]
