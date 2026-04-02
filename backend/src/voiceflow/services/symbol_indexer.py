"""symbol_indexer.py — Kod tabanından class/struct/func/enum sembollerini çıkar.

Desteklenen diller: Swift, Dart, Python, TypeScript/JavaScript, Go, Kotlin

Her sembol için: file_path + symbol_name + symbol_type + line_number
"""

import re
import logging
from pathlib import Path

import aiosqlite
import jellyfish

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


_JW_THRESHOLD = 0.85
_TR_SUFFIX_RE = re.compile(r"'[a-zA-ZığüşöçİĞÜŞÖÇ]+$")


def _strip_tr_suffix(word: str) -> str:
    """'PasteService'i → 'PasteService', possessive/case suffixes after apostrophe."""
    return _TR_SUFFIX_RE.sub("", word)


def _split_pascal(name: str) -> list[str]:
    """PascalCase → lowercase word parts. 'PasteService' → ['paste', 'service']"""
    parts = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', name)
    parts = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', parts)
    return [p.lower() for p in parts.split() if len(p) > 1]


def _phonetic_match(sym_parts: list[str], text_words: list[str]) -> bool:
    """True if every sym_part phonetically matches its text_word.

    Strategy: Jaro-Winkler on Metaphone codes (not raw words).
    This handles:
      'paste' → PST,  'pace' → PS    → meta_JW 0.91 ✓
      'menu'  → MN,   'many' → MN    → meta_JW 1.00 ✓
      'view'  → F,    'viu'  → F     → meta_JW 1.00 ✓
      'service' → SRFS, 'servisi' → SRFS  → meta_JW 1.00 ✓
    """
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


_PUNCT_STRIP = re.compile(r'^[\W_]+|[\W_]+$')


def _clean_word(w: str) -> str:
    """Strip leading/trailing punctuation for matching (keeps inner chars)."""
    return _PUNCT_STRIP.sub("", w)


async def inject_symbol_refs(text: str, user_id: str) -> str:
    """Metindeki bilinen sembolleri tespit et, yerinde @file:line SymbolName ile değiştir.

    Üç pass:
    0. Explicit @-trigger: "at Word" or "@Word" → force lookup, no part-count restriction
    1. Exact: PascalCase token → DB name lookup
    2. Full-name JW fuzzy: unresolved PascalCase tokens (OutService → AuthService)
    3. Phonetic sliding window: lowercase multi-word matches (paste service → PasteService)

    Örnekler:
      "at server"                → "@server.ts:1 Server" (explicit trigger, no restriction)
      "OutService nedir"         → "@auth_service.py:1 AuthService nedir"
      "paste service detayları"  → "@PasteService.swift:3 PasteService detayları"
      "many bar controller"      → "@MenuBarController.swift:9 MenuBarController"
    """
    words = text.split()
    if not words:
        return text

    # replacements: (start_word_idx, end_word_idx_exclusive, replacement_str)
    replacements: list[tuple[int, int, str]] = []
    seen: set[str] = set()   # matched symbol names
    covered: set[int] = set()  # word indices already replaced

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # ── Pass 0: explicit @-trigger ───────────────────────────────────────
        # "at Word" or "@Word" → user explicitly wants a symbol ref, bypass all filters
        # Whisper outputs "@" as "at" in speech, or keeps "@" if already in text.
        all_syms_for_at: list[dict] | None = None
        i = 0
        while i < len(words):
            raw = words[i]
            query: str | None = None
            span_end = i + 1

            if raw.startswith('@') and len(raw) > 1:
                # "@Server" — Whisper kept the @ symbol
                query = _clean_word(raw[1:])
            elif raw.lower() in {'at', 'et', 'ed', 'edd', 'add', 'hat', 'it'} and i + 1 < len(words):
                # "at/et/add/edd Word" — Whisper phonetic variants of @ symbol
                query = _clean_word(words[i + 1])
                span_end = i + 2

            if query and query not in seen:
                _AT_JW = 0.91

                def _len_ok(a: str, b: str) -> bool:
                    return min(len(a), len(b)) / max(len(a), len(b)) >= 0.55 if a and b else False

                async def _exact(q: str) -> dict | None:
                    async with db.execute(
                        """SELECT symbol_name, file_path, line_number, symbol_type
                           FROM symbol_index
                           WHERE user_id = ? AND LOWER(symbol_name) = LOWER(?)
                             AND symbol_type IN ('class','struct','protocol','enum','interface','object','module')
                           ORDER BY CASE symbol_type WHEN 'class' THEN 0 WHEN 'struct' THEN 1 ELSE 2 END
                           LIMIT 1""",
                        (user_id, q),
                    ) as cur:
                        return await cur.fetchone()

                # 1. Exact 1-word match (most precise — preserves rest of sentence)
                row = await _exact(query)

                if not row and raw.lower() in {'at', 'et', 'ed', 'edd', 'add', 'hat', 'it'} and i + 2 < len(words):
                    # 2. Exact 2-word match: "out service" → "OutService"
                    q2 = query + " " + _clean_word(words[i + 2])
                    row = await _exact(q2)
                    if row:
                        span_end = i + 3

                if not row:
                    # 3. Fuzzy — load all symbols once
                    if all_syms_for_at is None:
                        async with db.execute(
                            """SELECT symbol_name, file_path, line_number, symbol_type
                               FROM symbol_index WHERE user_id = ?
                               AND symbol_type IN ('class','struct','protocol','enum','interface','object','module')""",
                            (user_id,),
                        ) as cursor:
                            all_syms_for_at = [dict(r) for r in await cursor.fetchall()]

                    # Try 2-word compact first: "out service" → "outservice" vs "authservice"
                    # Slightly lower threshold for 2-word since user explicitly said both words
                    if raw.lower() in {'at', 'et', 'ed', 'edd', 'add', 'hat', 'it'} and i + 2 < len(words):
                        q2_compact = (query + _clean_word(words[i + 2])).lower()
                        best_score, best_row = 0.0, None
                        for sym in all_syms_for_at:
                            sym_lower = sym['symbol_name'].lower()
                            if not _len_ok(q2_compact, sym_lower):
                                continue
                            score = jellyfish.jaro_winkler_similarity(q2_compact, sym_lower)
                            if score > best_score:
                                best_score, best_row = score, sym
                        if best_score >= 0.90:
                            row = best_row
                            span_end = i + 3

                    # 1-word fuzzy fallback
                    if not row:
                        q_lower = query.lower()
                        best_score, best_row = 0.0, None
                        for sym in all_syms_for_at:
                            sym_lower = sym['symbol_name'].lower()
                            if not _len_ok(q_lower, sym_lower):
                                continue
                            score = jellyfish.jaro_winkler_similarity(q_lower, sym_lower)
                            if score > best_score:
                                best_score, best_row = score, sym
                        if best_score >= _AT_JW:
                            row = best_row
                            span_end = i + 2

                if row:
                    repl = f"@{row['file_path']}:{row['line_number']} {row['symbol_name']}"
                    replacements.append((i, span_end, repl))
                    seen.add(row['symbol_name'])
                    covered.update(range(i, span_end))
                    i = span_end
                    continue
            i += 1

        # ── Pass 0b: folder trigger ──────────────────────────────────────────
        # "folder services" / "klasör services" → "@backend/src/voiceflow/services/"
        _FOLDER_TRIGGERS = {'folder', 'folcder', 'klasör', 'klasor', 'dir', 'dizin', 'directory', 'foldır', 'foldir'}
        i = 0
        while i < len(words):
            raw = words[i]
            if raw.lower() in _FOLDER_TRIGGERS and i + 1 < len(words) and i not in covered:
                dir_query = _clean_word(words[i + 1]).lower()
                if dir_query:
                    # Extract unique directories from indexed file_path entries
                    async with db.execute(
                        "SELECT DISTINCT file_path FROM symbol_index WHERE user_id = ?",
                        (user_id,),
                    ) as cursor:
                        all_paths = [row[0] for row in await cursor.fetchall()]

                    # Collect all directory segments from paths
                    # Exclude vendor/generated dirs; max depth 5 to avoid Pods noise
                    _NOISE_DIRS = {'pods', 'node_modules', 'build', '.build', 'deriveddata',
                                   '__pycache__', '.venv', 'dist', 'vendor', 'carthage'}
                    dir_scores: dict[str, float] = {}
                    for fp in all_paths:
                        parts = fp.replace("\\", "/").split("/")
                        if any(p.lower() in _NOISE_DIRS for p in parts):
                            continue
                        for depth in range(1, min(len(parts), 6)):  # max depth 5
                            dir_path = "/".join(parts[:depth]) + "/"
                            dir_name = parts[depth - 1].lower()
                            if not dir_name:
                                continue
                            score = jellyfish.jaro_winkler_similarity(dir_query, dir_name)
                            if score > dir_scores.get(dir_path, 0):
                                dir_scores[dir_path] = score

                    if dir_scores:
                        threshold = 0.85
                        top_score = max(dir_scores.values())
                        if top_score >= threshold:
                            # All dirs at the top score (ties = multiple projects have same dir name)
                            top_dirs = sorted(
                                [d for d, s in dir_scores.items() if s >= top_score - 0.001],
                                key=len,
                            )
                            repl = " ".join(f"@{d}" for d in top_dirs)
                            replacements.append((i, i + 2, repl))
                            covered.update([i, i + 1])
                            i += 2
                            continue
            i += 1

        # ── Pass 1: exact PascalCase match ──────────────────────────────────
        # Single-word module entries (file-derived) are too generic — require 2+ parts.
        # Explicit class/struct/etc. definitions are allowed even if single-word.
        for i, word in enumerate(words):
            clean = _clean_word(word)
            if not re.match(r'^[A-Z][a-zA-Z0-9]{3,}$', clean):
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
                    # Module entries (file-derived) need 2+ parts — too generic otherwise
                    if row['symbol_type'] == 'module' and len(_split_pascal(row['symbol_name'])) < 2:
                        continue
                    repl = f"@{row['file_path']}:{row['line_number']} {row['symbol_name']}"
                    replacements.append((i, i + 1, repl))
                    seen.add(row['symbol_name'])
                    covered.add(i)

        # ── Pass 1.5: full-name JW fuzzy for unresolved PascalCase tokens ───
        # Same rule: module single-word excluded
        unresolved_pascal: list[tuple[str, int]] = [
            (_clean_word(words[i]), i)
            for i in range(len(words))
            if i not in covered
            and re.match(r'^[A-Z][a-zA-Z0-9]{3,}$', _clean_word(words[i]))
            and _clean_word(words[i]) not in seen
        ]
        if unresolved_pascal:
            async with db.execute(
                """SELECT symbol_name, file_path, line_number, symbol_type
                   FROM symbol_index
                   WHERE user_id = ?
                     AND symbol_type IN ('class','struct','protocol','enum','interface','object','module')""",
                (user_id,),
            ) as cursor:
                candidate_syms = [dict(r) for r in await cursor.fetchall()]

            for token, widx in unresolved_pascal:
                if widx in covered:
                    continue
                token_lower = token.lower()
                best_score, best_sym = 0.0, None
                for sym in candidate_syms:
                    if sym['symbol_name'] in seen:
                        continue
                    score = jellyfish.jaro_winkler_similarity(token_lower, sym['symbol_name'].lower())
                    if score > best_score:
                        best_score, best_sym = score, sym
                if best_score >= _JW_THRESHOLD and best_sym:
                    if best_sym.get('symbol_type') == 'module' and len(_split_pascal(best_sym['symbol_name'])) < 2:
                        continue
                    repl = f"@{best_sym['file_path']}:{best_sym['line_number']} {best_sym['symbol_name']}"
                    replacements.append((widx, widx + 1, repl))
                    seen.add(best_sym['symbol_name'])
                    covered.add(widx)

        # ── Pass 2: phonetic sliding-window match ────────────────────────────
        async with db.execute(
            """SELECT symbol_name, file_path, line_number
               FROM symbol_index
               WHERE user_id = ?
                 AND symbol_type IN ('class','struct','protocol','enum','interface','object','module')""",
            (user_id,),
        ) as cursor:
            all_symbols = [dict(r) for r in await cursor.fetchall()]

        if all_symbols:
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
                            repl = f"@{sym['file_path']}:{sym['line_number']} {sym['symbol_name']}"
                            replacements.append((i, i + size, repl))
                            seen.add(sym['symbol_name'])
                            covered.update(range(i, i + size))
                            break

    if not replacements:
        return text

    # Apply in reverse order to preserve word indices
    replacements.sort(key=lambda x: x[0], reverse=True)
    result = list(words)
    for start, end, repl in replacements:
        result[start:end] = [repl]

    # Remove stray "at" left before an injected @-ref (Pass 2 matched, Pass 0 didn't consume "at")
    cleaned: list[str] = []
    for j, w in enumerate(result):
        if w.lower() in {'at', 'et', 'ed', 'edd', 'add', 'hat', 'it', 'folder', 'folcder', 'klasör', 'klasor', 'dir', 'dizin', 'directory', 'foldır', 'foldir'} and j + 1 < len(result) and result[j + 1].startswith('@'):
            continue
        cleaned.append(w)

    return " ".join(cleaned)


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
