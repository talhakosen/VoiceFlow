"""symbol/injector.py — Inject symbol references into transcribed text.

Called only for Cmd-held segments (intent signal = Cmd key held).
Four-pass matching: directory names, exact PascalCase, JW fuzzy, phonetic window.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

import jellyfish

from ..db.storage import get_symbol_index_file_paths, get_symbols_for_matching

logger = logging.getLogger(__name__)

# ── Helpers ────────────────────────────────────────────────────────────────────
_PUNCT_STRIP = re.compile(r'^[\W_]+|[\W_]+$')


def _clean_word(w: str) -> str:
    """Strip leading/trailing punctuation for matching (keeps inner chars)."""
    return _PUNCT_STRIP.sub("", w)


_FS_NOISE_DIRS = {'pods', 'node_modules', 'build', '.build', 'deriveddata',
                  '__pycache__', '.venv', 'dist', 'vendor', 'carthage',
                  '.git', '.svn', 'target', 'out', '.gradle'}


def _fs_scan(root: Path, dir_query: str, dir_scores: dict[str, float], max_depth: int = 4) -> None:
    """Filesystem walk to find directories matching dir_query."""
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
    """'PasteService'i -> 'PasteService'"""
    return _TR_SUFFIX_RE.sub("", word)


def _split_pascal(name: str) -> list[str]:
    """PascalCase -> lowercase parts. 'PasteService' -> ['paste', 'service']"""
    parts = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', name)
    parts = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', parts)
    return [p.lower() for p in parts.split() if len(p) > 1]


def _phonetic_match(sym_parts: list[str], text_words: list[str]) -> bool:
    """Check if sym_parts phonetically match text_words."""
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
    """Cmd-held segment metnindeki dizin ve sembolleri tespit et, @ref ile degistir.

    SADECE cmd-held segmentler icin cagrilir -- normal konusmada cagrilmaz.
    Tetikleyici sozcuk gerekmez; Cmd tusu zaten niyet sinyali.

    Pass 0: directory name matching ("voiceflow" -> @VoiceFlowApp/)
    Pass 1: exact PascalCase token -> DB exact match
    Pass 2: JW fuzzy PascalCase (OutService -> AuthService)
    Pass 3: phonetic sliding window ("recording service" -> RecordingService)
    """
    words = text.split()
    if not words:
        return text

    replacements: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    covered: set[int] = set()

    # ── Pre-load all needed data from DB ─────────────────────────────────────
    _SYMBOL_TYPES = ("class", "struct", "protocol", "enum", "interface", "object", "module")
    file_rows_raw = await get_symbol_index_file_paths(user_id)
    all_symbols_db = await get_symbols_for_matching(user_id, symbol_types=_SYMBOL_TYPES)

    # ── Pass 0: directory name matching ───────────────────────────────────
    dir_map: dict[str, list[str]] = {}

    def _dir_map_add(key: str, rel: str) -> None:
        lst = dir_map.setdefault(key, [])
        if rel not in lst:
            lst.append(rel)

    project_roots: set[str] = set()
    for row in file_rows_raw:
        proj_path, file_path = row["project_path"], row["file_path"]
        project_roots.add(proj_path)
        parts = Path(file_path).parts
        for depth in range(1, len(parts)):
            dname = parts[depth - 1]
            rel = "/".join(parts[:depth]) + "/"
            _dir_map_add(dname.lower(), rel)

    _SCRIPT_EXTS = {".sh", ".js", ".ts", ".py", ".yaml", ".yml", ".json", ".toml"}
    for root_str in project_roots:
        root_p = Path(root_str)
        if not root_p.exists():
            continue
        for dirpath_str, dirnames, filenames in os.walk(str(root_p)):
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
                _dir_map_add(dname.lower(), rel)
            for fname in filenames:
                fp = Path(fname)
                if fp.suffix.lower() in _SCRIPT_EXTS:
                    stem = fp.stem.lower()
                    if len(stem) >= 4 and not stem.startswith('.'):
                        rel_file = str(rel_p / fname) if str(rel_p) != "." else fname
                        _dir_map_add(stem, rel_file)

    # Build exact-match lookup dict from pre-loaded symbols (Pass 1)
    exact_lookup: dict[str, dict] = {}
    for sym in all_symbols_db:
        key = sym["symbol_name"].lower()
        existing = exact_lookup.get(key)
        if existing is None:
            exact_lookup[key] = sym
        else:
            # Prefer class > struct > others
            order = {"class": 0, "struct": 1}
            if order.get(sym["symbol_type"], 2) < order.get(existing["symbol_type"], 2):
                exact_lookup[key] = sym

    # ── Pass 1: exact PascalCase match ────────────────────────────────────
    for i, word in enumerate(words):
        clean = _clean_word(word)
        if not re.match(r'^[A-Z][a-zA-Z0-9]{2,}$', clean):
            continue
        if clean in seen or i in covered:
            continue
        row = exact_lookup.get(clean.lower())
        if row:
            if row['symbol_type'] == 'module' and len(_split_pascal(row['symbol_name'])) < 2:
                continue
            replacements.append((i, i + 1, f"@{row['file_path']}:{row['line_number']} {row['symbol_name']}"))
            seen.add(row['symbol_name'])
            covered.add(i)

    # ── Pass 2: JW fuzzy for unresolved PascalCase tokens ─────────────────
    unresolved = [
        (_clean_word(words[i]), i)
        for i in range(len(words))
        if i not in covered and re.match(r'^[A-Z][a-zA-Z0-9]{2,}$', _clean_word(words[i]))
        and _clean_word(words[i]) not in seen
    ]
    if unresolved:
        candidates = all_symbols_db  # already loaded

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

    # ── Pass 3: phonetic sliding window ───────────────────────────────────

        sym_by_len: dict[int, list[tuple[list[str], dict]]] = {}
        for sym in all_symbols_db:
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

        # ── Pass 0: directory matching (runs last — only on uncovered tokens) ──
        if dir_map:
            def _dir_score(token: str, dname_lower: str) -> float:
                if dname_lower.startswith(token) and len(token) >= 5:
                    return 0.95
                if token.startswith(dname_lower) and len(dname_lower) >= 5:
                    if len(token) <= len(dname_lower) * 1.4:
                        return 0.90
                return jellyfish.jaro_winkler_similarity(token, dname_lower)

            def _best_dir(token: str) -> tuple[float, list[str]]:
                best_score, best_rels = 0.0, []
                for dname_lower, rels in dir_map.items():
                    s = _dir_score(token, dname_lower)
                    if s > best_score:
                        best_score, best_rels = s, rels
                return best_score, best_rels

            def _fmt_refs(rels: list[str]) -> str:
                return " ".join(f"@{r}" for r in sorted(set(rels)))

            i = 0
            while i < len(words):
                if i in covered:
                    i += 1
                    continue
                matched = False
                if i + 1 < len(words) and (i + 1) not in covered:
                    bigram = (_clean_word(words[i]) + _clean_word(words[i + 1])).lower()
                    _, best_rels_check = _best_dir(bigram)
                    best_dname = best_rels_check[0].rstrip("/").split("/")[-1] if best_rels_check else ""
                    len_ok = best_dname and len(bigram) <= len(best_dname) * 1.5
                    if len(bigram) >= _DIR_MIN_LEN and len_ok:
                        score, rels = _best_dir(bigram)
                        new_rels = [r for r in rels if r not in seen]
                        if score >= _DIR_THRESHOLD and new_rels:
                            ref_str = _fmt_refs(new_rels)
                            replacements.append((i, i + 2, ref_str))
                            seen.update(new_rels)
                            covered.update([i, i + 1])
                            logger.info("Pass 0 dir bigram: '%s' -> %s (%.2f)", bigram, ref_str, score)
                            matched = True
                if not matched:
                    token = _clean_word(words[i]).lower()
                    if len(token) >= _DIR_MIN_LEN:
                        score, rels = _best_dir(token)
                        new_rels = [r for r in rels if r not in seen]
                        if score >= _DIR_THRESHOLD and new_rels:
                            ref_str = _fmt_refs(new_rels)
                            replacements.append((i, i + 1, ref_str))
                            seen.update(new_rels)
                            covered.add(i)
                            logger.info("Pass 0 dir unigram: '%s' -> %s (%.2f)", token, ref_str, score)
                i += 1

    if not replacements:
        return text

    replacements.sort(key=lambda x: x[0], reverse=True)
    result = list(words)
    for start, end, repl in replacements:
        result[start:end] = [repl]
    return " ".join(result)
