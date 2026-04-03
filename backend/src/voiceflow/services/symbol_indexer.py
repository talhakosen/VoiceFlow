"""symbol_indexer.py — Kod tabanından class/struct/func/enum sembollerini çıkar.

Desteklenen diller: Swift, Dart, Python, TypeScript/JavaScript, Go, Kotlin

Her sembol için: file_path + symbol_name + symbol_type + line_number
"""

import os
import re
import logging
from pathlib import Path

import aiosqlite
import jellyfish

logger = logging.getLogger(__name__)

from ..db.storage import DB_PATH

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

        # File-level module entry: auth_service.py → AuthService (module type)
        stem = file_path.stem
        module_name = "".join(w.capitalize() for w in stem.split("_"))
        if len(module_name) >= 3:
            all_symbols.append({
                "file_path": str(file_path.relative_to(root)),
                "symbol_type": "module",
                "symbol_name": module_name,
                "line_number": 1,
            })

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



_PUNCT_STRIP = re.compile(r'^[\W_]+|[\W_]+$')


def _clean_word(w: str) -> str:
    """Strip leading/trailing punctuation for matching (keeps inner chars)."""
    return _PUNCT_STRIP.sub("", w)


_FS_NOISE_DIRS = {'pods', 'node_modules', 'build', '.build', 'deriveddata',
                  '__pycache__', '.venv', 'dist', 'vendor', 'carthage',
                  '.git', '.svn', 'target', 'out', '.gradle'}


def _fs_scan(root: Path, dir_query: str, dir_scores: dict[str, float], max_depth: int = 4) -> None:
    """Filesystem walk to find directories matching dir_query.

    Fallback for non-code dirs (templates/, assets/, etc.) that have no
    indexed symbols and therefore don't appear in symbol_index.file_path.
    Paths are relative to root, consistent with symbol_index storage.
    """
    for dirpath_str, dirnames, _ in os.walk(str(root)):
        dirpath = Path(dirpath_str)
        try:
            rel = dirpath.relative_to(root)
        except ValueError:
            continue
        depth = len(rel.parts)
        if depth >= max_depth:
            dirnames.clear()
            continue
        dirnames[:] = [d for d in dirnames
                       if d.lower() not in _FS_NOISE_DIRS and not d.startswith('.')]
        for dname in dirnames:
            score = jellyfish.jaro_winkler_similarity(dir_query, dname.lower())
            rel_dir = (str(rel / dname) if str(rel) != "." else dname).replace("\\", "/") + "/"
            if score > dir_scores.get(rel_dir, 0.0):
                dir_scores[rel_dir] = score


_JW_THRESHOLD = 0.85
_TR_SUFFIX_RE = re.compile(r"'[a-zA-ZığüşöçİĞÜŞÖÇ]+$")


def _strip_tr_suffix(word: str) -> str:
    """'PasteService'i → 'PasteService'"""
    return _TR_SUFFIX_RE.sub("", word)


def _split_pascal(name: str) -> list[str]:
    """PascalCase → lowercase parts. 'PasteService' → ['paste', 'service']"""
    parts = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', name)
    parts = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', parts)
    return [p.lower() for p in parts.split() if len(p) > 1]


def _phonetic_match(sym_parts: list[str], text_words: list[str]) -> bool:
    """Her sym_part, karşılık gelen text_word ile fonetik eşleşiyor mu."""
    if len(sym_parts) != len(text_words):
        return False
    for sp, tw in zip(sym_parts, text_words):
        clean = _strip_tr_suffix(tw).lower()
        if not clean:
            return False
        meta_sp = jellyfish.metaphone(sp) or sp
        meta_tw = jellyfish.metaphone(clean) or clean
        if jellyfish.jaro_winkler_similarity(meta_sp, meta_tw) < _JW_THRESHOLD:
            return False
    return True


_DIR_THRESHOLD = 0.82
_DIR_MIN_LEN = 4


async def inject_symbol_refs(text: str, user_id: str) -> str:
    """Cmd-held segment metnindeki dizin ve sembolleri tespit et, @ref ile değiştir.

    SADECE cmd-held segmentler için çağrılır — normal konuşmada çağrılmaz.
    Tetikleyici sözcük gerekmez; Cmd tuşu zaten niyet sinyali.

    Pass 0: directory name matching ("voiceflow" → @VoiceFlowApp/)
    Pass 1: exact PascalCase token → DB exact match
    Pass 2: JW fuzzy PascalCase (OutService → AuthService)
    Pass 3: phonetic sliding window ("recording service" → RecordingService)
    """
    words = text.split()
    if not words:
        return text

    replacements: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    covered: set[int] = set()

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # ── Pass 0: directory name matching ─────────────────────────────────
        # Collect all known dir names from indexed file paths + filesystem scan
        dir_map: dict[str, str] = {}  # lowercase_dirname → rel_path/

        async with db.execute(
            "SELECT DISTINCT project_path, file_path FROM symbol_index WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            file_rows = await cursor.fetchall()

        project_roots: set[str] = set()
        for row in file_rows:
            proj_path, file_path = row[0], row[1]
            project_roots.add(proj_path)
            parts = Path(file_path).parts
            for depth in range(1, len(parts)):
                dname = parts[depth - 1]
                rel = "/".join(parts[:depth]) + "/"
                dir_map.setdefault(dname.lower(), rel)

        # Filesystem scan for non-code dirs not in symbol_index
        for root_str in project_roots:
            root_p = Path(root_str)
            if not root_p.exists():
                continue
            for dirpath_str, dirnames, _ in os.walk(str(root_p)):
                dirpath = Path(dirpath_str)
                try:
                    rel_p = dirpath.relative_to(root_p)
                except ValueError:
                    continue
                depth_p = len(rel_p.parts)
                if depth_p >= 4:
                    dirnames.clear()
                    continue
                dirnames[:] = [d for d in dirnames
                               if d.lower() not in _FS_NOISE_DIRS and not d.startswith('.')]
                for dname in dirnames:
                    rel = (str(rel_p / dname) if str(rel_p) != "." else dname) + "/"
                    dir_map.setdefault(dname.lower(), rel)

        if dir_map:
            def _dir_score(token: str, dname_lower: str) -> float:
                """Bir token'ın bir dizin adına benzerlik skorunu hesapla."""
                if dname_lower.startswith(token) and len(token) >= 5:
                    return 0.95
                if token.startswith(dname_lower) and len(dname_lower) >= 5:
                    return 0.90
                return jellyfish.jaro_winkler_similarity(token, dname_lower)

            def _best_dir(token: str) -> tuple[float, str | None]:
                best_score, best_rel = 0.0, None
                for dname_lower, rel in dir_map.items():
                    s = _dir_score(token, dname_lower)
                    if s > best_score:
                        best_score, best_rel = s, rel
                return best_score, best_rel

            # Try window=2 (bigram) first to handle Whisper word splits
            # e.g. "Voice flow" → "voiceflow" → @VoiceFlowApp/
            i = 0
            while i < len(words):
                if i in covered:
                    i += 1
                    continue
                matched = False
                if i + 1 < len(words) and (i + 1) not in covered:
                    bigram = (_clean_word(words[i]) + _clean_word(words[i + 1])).lower()
                    if len(bigram) >= _DIR_MIN_LEN:
                        score, rel = _best_dir(bigram)
                        if score >= _DIR_THRESHOLD and rel and rel not in seen:
                            replacements.append((i, i + 2, f"@{rel}"))
                            seen.add(rel)
                            covered.update([i, i + 1])
                            logger.info("Pass 0 dir bigram: '%s' → @%s (%.2f)", bigram, rel, score)
                            matched = True
                if not matched:
                    token = _clean_word(words[i]).lower()
                    if len(token) >= _DIR_MIN_LEN:
                        score, rel = _best_dir(token)
                        if score >= _DIR_THRESHOLD and rel and rel not in seen:
                            replacements.append((i, i + 1, f"@{rel}"))
                            seen.add(rel)
                            covered.add(i)
                            logger.info("Pass 0 dir unigram: '%s' → @%s (%.2f)", token, rel, score)
                i += 1

        # ── Pass 1: exact PascalCase match ──────────────────────────────────
        for i, word in enumerate(words):
            clean = _clean_word(word)
            if not re.match(r'^[A-Z][a-zA-Z0-9]{2,}$', clean):
                continue
            if clean in seen or i in covered:
                continue
            async with db.execute(
                """SELECT symbol_name, file_path, line_number, symbol_type
                   FROM symbol_index
                   WHERE user_id = ? AND LOWER(symbol_name) = LOWER(?)
                     AND symbol_type IN ('class','struct','protocol','enum','interface','object','module')
                   ORDER BY CASE symbol_type WHEN 'class' THEN 0 WHEN 'struct' THEN 1 ELSE 2 END
                   LIMIT 1""",
                (user_id, clean),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    if row['symbol_type'] == 'module' and len(_split_pascal(row['symbol_name'])) < 2:
                        continue
                    replacements.append((i, i + 1, f"@{row['file_path']}:{row['line_number']} {row['symbol_name']}"))
                    seen.add(row['symbol_name'])
                    covered.add(i)

        # ── Pass 2: JW fuzzy for unresolved PascalCase tokens ───────────────
        unresolved = [
            (_clean_word(words[i]), i)
            for i in range(len(words))
            if i not in covered and re.match(r'^[A-Z][a-zA-Z0-9]{2,}$', _clean_word(words[i]))
            and _clean_word(words[i]) not in seen
        ]
        if unresolved:
            async with db.execute(
                """SELECT symbol_name, file_path, line_number, symbol_type
                   FROM symbol_index WHERE user_id = ?
                   AND symbol_type IN ('class','struct','protocol','enum','interface','object','module')""",
                (user_id,),
            ) as cursor:
                candidates = [dict(r) for r in await cursor.fetchall()]

            for token, widx in unresolved:
                if widx in covered:
                    continue
                best_score, best_sym = 0.0, None
                for sym in candidates:
                    if sym['symbol_name'] in seen:
                        continue
                    score = jellyfish.jaro_winkler_similarity(token.lower(), sym['symbol_name'].lower())
                    if score > best_score:
                        best_score, best_sym = score, sym
                if best_score >= _JW_THRESHOLD and best_sym:
                    if best_sym['symbol_type'] == 'module' and len(_split_pascal(best_sym['symbol_name'])) < 2:
                        continue
                    replacements.append((widx, widx + 1, f"@{best_sym['file_path']}:{best_sym['line_number']} {best_sym['symbol_name']}"))
                    seen.add(best_sym['symbol_name'])
                    covered.add(widx)

        # ── Pass 3: phonetic sliding window ─────────────────────────────────
        async with db.execute(
            """SELECT symbol_name, file_path, line_number FROM symbol_index
               WHERE user_id = ?
               AND symbol_type IN ('class','struct','protocol','enum','interface','object','module')""",
            (user_id,),
        ) as cursor:
            all_symbols = [dict(r) for r in await cursor.fetchall()]

        sym_by_len: dict[int, list[tuple[list[str], dict]]] = {}
        for sym in all_symbols:
            if sym['symbol_name'] in seen:
                continue
            parts = _split_pascal(sym['symbol_name'])
            if len(parts) >= 2:
                sym_by_len.setdefault(len(parts), []).append((parts, sym))

        for i in range(len(words)):
            if i in covered:
                continue
            for size, candidates in sym_by_len.items():
                if i + size > len(words):
                    continue
                if any(j in covered for j in range(i, i + size)):
                    continue
                window = [_clean_word(w) for w in words[i:i + size]]
                for sym_parts, sym in candidates:
                    if sym['symbol_name'] in seen:
                        continue
                    if _phonetic_match(sym_parts, window):
                        replacements.append((i, i + size, f"@{sym['file_path']}:{sym['line_number']} {sym['symbol_name']}"))
                        seen.add(sym['symbol_name'])
                        covered.update(range(i, i + size))
                        break

    if not replacements:
        return text

    replacements.sort(key=lambda x: x[0], reverse=True)
    result = list(words)
    for start, end, repl in replacements:
        result[start:end] = [repl]
    return " ".join(result)


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
