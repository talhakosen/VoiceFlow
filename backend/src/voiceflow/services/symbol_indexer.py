"""Symbol indexer — tree-sitter based AST analysis.

Supported languages: Swift, Python, TypeScript, JavaScript, Kotlin, Go
Output: symbol_index_v2 (enriched) + symbol_index (backward compat flat)
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import aiosqlite
import jellyfish

from ..core.config import DB_PATH

logger = logging.getLogger(__name__)

# ── Language map ──────────────────────────────────────────────────────────────
_LANGUAGE_MAP: dict[str, str] = {
    ".swift": "swift",
    ".py":    "python",
    ".ts":    "typescript",
    ".tsx":   "tsx",
    ".js":    "javascript",
    ".jsx":   "javascript",
    ".kt":    "kotlin",
    ".go":    "go",
}

_MAX_FILE_BYTES = 500_000
_SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", "build", "dist",
              "DerivedData", ".build", "Pods", "vendor", ".claude", "worktrees"}


# ── SymbolInfo dataclass ──────────────────────────────────────────────────────
@dataclass
class SymbolInfo:
    file_path:     str
    symbol_type:   str   # class, struct, protocol, enum, interface, func, prop, type
    symbol_name:   str
    line_number:   int
    end_line:      int | None = None
    signature:     str | None = None
    parent_symbol: str | None = None   # enclosing class (for methods)
    parent_class:  str | None = None   # inheritance
    conformances:  str | None = None   # protocol/interface conformance (comma-sep)
    return_type:   str | None = None
    properties:    list[dict] = field(default_factory=list)
    imports:       list[str]  = field(default_factory=list)
    decorators:    list[str]  = field(default_factory=list)
    visibility:    str | None = None
    is_static:     bool = False


# ── TreeSitterExtractor ───────────────────────────────────────────────────────
class TreeSitterExtractor:
    """Lazy-loaded per-language parsers using individual tree-sitter-* packages."""

    def __init__(self):
        self._parsers: dict[str, Any] = {}
        self._languages: dict[str, Any] = {}

    def _get_parser(self, lang: str):
        if lang not in self._parsers:
            try:
                from tree_sitter import Language, Parser
                lang_ptr = self._get_language_ptr(lang)
                if lang_ptr is None:
                    return None, None
                language = Language(lang_ptr)
                parser = Parser(language)
                self._parsers[lang] = parser
                self._languages[lang] = language
            except Exception as e:
                logger.warning("tree-sitter %s unavailable: %s", lang, e)
                return None, None
        return self._parsers[lang], self._languages[lang]

    @staticmethod
    def _get_language_ptr(lang: str):
        """Get the language pointer from the appropriate tree-sitter-* package."""
        try:
            if lang == "swift":
                import tree_sitter_swift
                return tree_sitter_swift.language()
            elif lang == "python":
                import tree_sitter_python
                return tree_sitter_python.language()
            elif lang == "typescript":
                import tree_sitter_typescript
                return tree_sitter_typescript.language_typescript()
            elif lang == "tsx":
                import tree_sitter_typescript
                return tree_sitter_typescript.language_tsx()
            elif lang == "javascript":
                import tree_sitter_javascript
                return tree_sitter_javascript.language()
            elif lang == "go":
                import tree_sitter_go
                return tree_sitter_go.language()
            elif lang == "kotlin":
                import tree_sitter_kotlin
                return tree_sitter_kotlin.language()
        except ImportError:
            logger.debug("tree-sitter-%s package not installed", lang)
        return None

    @staticmethod
    def _node_text(node, source: bytes) -> str:
        return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

    def extract(self, file_path: Path, project_root: Path) -> list[SymbolInfo]:
        lang_name = _LANGUAGE_MAP.get(file_path.suffix.lower())
        if not lang_name:
            return []
        parser, language = self._get_parser(lang_name)
        if parser is None:
            return []
        try:
            source = file_path.read_bytes()
            if len(source) > _MAX_FILE_BYTES:
                return []
            tree = parser.parse(source)
            rel_path = str(file_path.relative_to(project_root))
        except Exception as e:
            logger.debug("parse error %s: %s", file_path, e)
            return []

        # If tree-sitter parse fails (ERROR root), fall back to regex
        if tree.root_node.has_error or tree.root_node.type == "ERROR":
            logger.debug("tree-sitter parse error for %s, falling back to regex", file_path.name)
            return self._extract_regex_fallback(source, rel_path, lang_name)

        extractors = {
            "swift":      self._extract_swift,
            "python":     self._extract_python,
            "typescript": self._extract_typescript,
            "tsx":        self._extract_typescript,
            "javascript": self._extract_typescript,  # reuse TS extractor
            "kotlin":     self._extract_kotlin,
            "go":         self._extract_go,
        }
        fn = extractors.get(lang_name)
        if fn is None:
            return []
        return fn(tree, source, rel_path, language)

    # ── Regex fallback for files where tree-sitter fails ─────────────────────
    _REGEX_EXTRACTORS: dict[str, list[tuple[str, re.Pattern]]] = {
        "swift": [
            ("class",    re.compile(r'^\s*(?:@\w+\s+)*(?:public |private |internal |open |final )*class\s+(\w+)', re.M)),
            ("struct",   re.compile(r'^\s*(?:@\w+\s+)*(?:public |private |internal )*struct\s+(\w+)', re.M)),
            ("enum",     re.compile(r'^\s*(?:@\w+\s+)*(?:public |private |internal )*enum\s+(\w+)', re.M)),
            ("protocol", re.compile(r'^\s*(?:@\w+\s+)*(?:public |private |internal )*protocol\s+(\w+)', re.M)),
            ("func",     re.compile(r'^\s*(?:@\w+\s+)*(?:public |private |internal |override |static |class )*func\s+(\w+)', re.M)),
        ],
        "python": [
            ("class",    re.compile(r'^class\s+(\w+)', re.M)),
            ("func",     re.compile(r'^(?:    )?(?:async )?def\s+(\w+)', re.M)),
        ],
        "typescript": [
            ("class",    re.compile(r'^\s*(?:export\s+)?(?:abstract\s+)?class\s+(\w+)', re.M)),
            ("interface", re.compile(r'^\s*(?:export\s+)?interface\s+(\w+)', re.M)),
            ("func",     re.compile(r'^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)', re.M)),
        ],
        "tsx": [],  # reuse typescript
        "javascript": [],  # reuse typescript
        "kotlin": [
            ("class",    re.compile(r'^\s*(?:data\s+|sealed\s+|abstract\s+|open\s+)?class\s+(\w+)', re.M)),
            ("func",     re.compile(r'^\s*(?:suspend\s+)?fun\s+(\w+)', re.M)),
        ],
        "go": [
            ("struct",   re.compile(r'^type\s+(\w+)\s+struct', re.M)),
            ("interface", re.compile(r'^type\s+(\w+)\s+interface', re.M)),
            ("func",     re.compile(r'^func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)', re.M)),
        ],
    }

    def _extract_regex_fallback(self, source: bytes, rel_path: str, lang_name: str) -> list[SymbolInfo]:
        """Regex-based symbol extraction for files where tree-sitter fails."""
        text = source.decode("utf-8", errors="ignore")
        extractors = self._REGEX_EXTRACTORS.get(lang_name)
        if not extractors:
            # Fallback to typescript extractors for tsx/javascript
            extractors = self._REGEX_EXTRACTORS.get("typescript", [])
        if not extractors:
            return []

        # Build line offset table
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
            return lo + 1

        # Extract imports (Swift)
        imports = []
        if lang_name == "swift":
            for m in re.finditer(r'^\s*import\s+(\w+)', text, re.M):
                imports.append(m.group(1))

        # Extract inheritance for classes/structs
        inheritance_map: dict[str, tuple[str | None, str | None]] = {}
        if lang_name == "swift":
            # Handles: class Foo: Bar, Baz {  AND  @Observable final class Foo: Bar {
            inh_re = re.compile(
                r'(?:class|struct|enum|actor)\s+(\w+)(?:\s*<[^>]*>)?\s*:\s*([^{<\n]+?)(?:\s*\{|\s*where\b)',
                re.M,
            )
            for m in inh_re.finditer(text):
                name = m.group(1)
                inh = m.group(2).strip()
                parts = [p.strip() for p in inh.split(",") if re.match(r'^[A-Z]\w*', p.strip())]
                parent = parts[0] if parts else None
                confs = ", ".join(parts[1:]) if len(parts) > 1 else None
                inheritance_map[name] = (parent, confs)

        symbols = []
        for symbol_type, pattern in extractors:
            for match in pattern.finditer(text):
                name = match.group(1)
                if len(name) < 2:
                    continue
                line = offset_to_line(match.start())
                parent_class, conformances = inheritance_map.get(name, (None, None))
                symbols.append(SymbolInfo(
                    file_path=rel_path,
                    symbol_type=symbol_type,
                    symbol_name=name,
                    line_number=line,
                    imports=imports,
                    parent_class=parent_class,
                    conformances=conformances,
                ))

        return symbols

    # ── Swift ─────────────────────────────────────────────────────────────────
    def _extract_swift(self, tree, source: bytes, rel_path: str, language) -> list[SymbolInfo]:
        symbols: list[SymbolInfo] = []
        root = tree.root_node
        imports = self._extract_swift_imports(root, source)
        self._walk_swift_node(root, source, rel_path, imports, symbols, parent=None)
        return symbols

    def _walk_swift_node(self, node, source, rel_path, imports, symbols, parent):
        """Walk Swift AST.

        Node types from AST dump:
        - class_declaration (for class, struct, enum — differentiated by declaration_kind field)
        - protocol_declaration
        - function_declaration
        """
        for child in node.children:
            ctype = child.type

            if ctype == "class_declaration":
                # declaration_kind field tells us: class, struct, or enum
                kind_node = child.child_by_field_name("declaration_kind")
                kind_text = self._node_text(kind_node, source) if kind_node else "class"
                kind_map = {"class": "class", "struct": "struct", "enum": "enum"}
                symbol_type = kind_map.get(kind_text, "class")

                name_node = child.child_by_field_name("name")
                if name_node is None:
                    continue
                name = self._node_text(name_node, source)
                line = child.start_point[0] + 1
                end_line = child.end_point[0] + 1

                # Inheritance / conformance — try AST nodes first, then text fallback
                parent_class = None
                conformances_list = []
                for n in child.children:
                    if n.type in ("inheritance_specifier", "type_inheritance_clause",
                                  "inheritance_constraint"):
                        inh_text = self._node_text(n, source).strip().lstrip(":")
                        for part in inh_text.split(","):
                            part = part.strip()
                            if part and re.match(r'^[A-Z]\w*', part):
                                if parent_class is None:
                                    parent_class = part
                                else:
                                    conformances_list.append(part)

                # Text fallback: look for "ClassName: TypeA, TypeB" in declaration header only
                if parent_class is None:
                    node_text = self._node_text(child, source)
                    # Only search the header — text before the opening brace of the body
                    header = node_text.split("{")[0]
                    m = re.search(
                        rf'\b{re.escape(name)}\s*(?:<[^>]*>)?\s*:\s*([A-Z][^{{<\n]+?)(?=\s*(?:\{{|where\b|$))',
                        header,
                    )
                    if m:
                        parts = [p.strip() for p in m.group(1).split(",")]
                        parts = [p for p in parts if re.match(r'^[A-Z]\w*', p)]
                        if parts:
                            parent_class = parts[0]
                            conformances_list = parts[1:]

                # Properties
                properties = self._extract_swift_properties(child, source)

                sym = SymbolInfo(
                    file_path=rel_path,
                    symbol_type=symbol_type,
                    symbol_name=name,
                    line_number=line,
                    end_line=end_line,
                    parent_symbol=parent,
                    parent_class=parent_class,
                    conformances=", ".join(conformances_list) if conformances_list else None,
                    properties=properties,
                    imports=imports,
                )
                symbols.append(sym)

                # Recurse into body for methods
                self._walk_swift_methods(child, source, rel_path, imports, symbols, parent=name)

            elif ctype == "protocol_declaration":
                name_node = child.child_by_field_name("name")
                if name_node is None:
                    # Fallback: find type_identifier
                    for n in child.children:
                        if n.type == "type_identifier":
                            name_node = n
                            break
                if name_node is None:
                    continue

                name = self._node_text(name_node, source)
                line = child.start_point[0] + 1
                end_line = child.end_point[0] + 1

                symbols.append(SymbolInfo(
                    file_path=rel_path,
                    symbol_type="protocol",
                    symbol_name=name,
                    line_number=line,
                    end_line=end_line,
                    parent_symbol=parent,
                    imports=imports,
                ))

                # Protocol methods
                for n in child.children:
                    if n.type == "protocol_body":
                        for gc in n.children:
                            if gc.type == "protocol_function_declaration":
                                self._add_swift_func(gc, source, rel_path, imports, symbols, parent=name)

            elif ctype == "function_declaration":
                self._add_swift_func(child, source, rel_path, imports, symbols, parent)

    def _walk_swift_methods(self, container, source, rel_path, imports, symbols, parent):
        """Find methods inside class/struct/enum body."""
        body = container.child_by_field_name("body")
        if body is None:
            # Fallback: look for class_body or enum_class_body
            for child in container.children:
                if child.type in ("class_body", "enum_class_body"):
                    body = child
                    break
        if body is None:
            return

        for child in body.children:
            if child.type == "function_declaration":
                self._add_swift_func(child, source, rel_path, imports, symbols, parent)

    def _add_swift_func(self, node, source, rel_path, imports, symbols, parent):
        # In Swift grammar, "name" field may match both the function name (simple_identifier)
        # and the return type. We need the simple_identifier specifically.
        name = None
        for n in node.children:
            if n.type == "simple_identifier":
                name = self._node_text(n, source)
                break
        if name is None:
            return

        line = node.start_point[0] + 1

        # Return type: find "->" then the next type node
        return_type = None
        found_arrow = False
        for n in node.children:
            if self._node_text(n, source) == "->":
                found_arrow = True
                continue
            if found_arrow and n.type not in ("->", "func", "simple_identifier", "(", ")", "parameter", ","):
                return_type = self._node_text(n, source).strip()
                break

        # Full signature (first line before {)
        full_text = self._node_text(node, source)
        signature = full_text.split("{")[0].strip()
        if len(signature) > 200:
            signature = signature[:200] + "..."

        # Static/class method detection
        is_static = False
        prev = node.prev_named_sibling
        if prev and prev.type == "modifiers":
            mod_text = self._node_text(prev, source)
            if "static" in mod_text or "class " in mod_text:
                is_static = True

        symbols.append(SymbolInfo(
            file_path=rel_path,
            symbol_type="func",
            symbol_name=name,
            line_number=line,
            end_line=node.end_point[0] + 1,
            signature=signature,
            parent_symbol=parent,
            return_type=return_type,
            imports=imports,
            is_static=is_static,
        ))

    def _extract_swift_imports(self, root, source: bytes) -> list[str]:
        imports = []
        for child in root.children:
            if child.type == "import_declaration":
                text = self._node_text(child, source)
                module = text.replace("import", "").strip()
                if module:
                    imports.append(module)
        return imports

    def _extract_swift_properties(self, container, source: bytes) -> list[dict]:
        props = []
        body = container.child_by_field_name("body")
        if body is None:
            for child in container.children:
                if child.type in ("class_body", "enum_class_body"):
                    body = child
                    break
        if body is None:
            return props
        for child in body.children:
            if child.type == "property_declaration":
                prop_text = self._node_text(child, source).split("{")[0].strip()
                props.append({"text": prop_text[:100]})
        return props

    # ── Python ────────────────────────────────────────────────────────────────
    def _extract_python(self, tree, source: bytes, rel_path: str, language) -> list[SymbolInfo]:
        symbols: list[SymbolInfo] = []
        root = tree.root_node
        imports = self._extract_python_imports(root, source)
        self._walk_python_node(root, source, rel_path, imports, symbols, parent=None, depth=0)
        return symbols

    def _walk_python_node(self, node, source, rel_path, imports, symbols, parent, depth):
        if depth > 3:
            return
        for child in node.children:
            if child.type == "class_definition":
                name_node = child.child_by_field_name("name")
                if name_node is None:
                    continue
                name = self._node_text(name_node, source)
                line = child.start_point[0] + 1

                # Base classes via "superclasses" field (argument_list node)
                bases_node = child.child_by_field_name("superclasses")
                parent_class = None
                conformances_list = []
                if bases_node:
                    # Parse identifiers inside argument_list
                    base_names = []
                    for n in bases_node.children:
                        if n.type == "identifier":
                            base_names.append(self._node_text(n, source))
                        elif n.type == "attribute":
                            base_names.append(self._node_text(n, source))
                    if base_names:
                        parent_class = base_names[0]
                        conformances_list = base_names[1:]

                # Decorators
                decorators = self._collect_python_decorators(child, source)

                symbols.append(SymbolInfo(
                    file_path=rel_path,
                    symbol_type="class",
                    symbol_name=name,
                    line_number=line,
                    end_line=child.end_point[0] + 1,
                    parent_symbol=parent,
                    parent_class=parent_class,
                    conformances=", ".join(conformances_list) if conformances_list else None,
                    imports=imports,
                    decorators=decorators,
                ))
                # Recurse into class body
                body = child.child_by_field_name("body")
                if body:
                    self._walk_python_node(body, source, rel_path, imports, symbols, parent=name, depth=depth + 1)

            elif child.type == "function_definition":
                self._add_python_func(child, source, rel_path, imports, symbols, parent)

            elif child.type == "decorated_definition":
                # decorated_definition wraps decorator + function_definition or class_definition
                for gc in child.children:
                    if gc.type == "function_definition":
                        self._add_python_func(gc, source, rel_path, imports, symbols, parent,
                                              decorators_from=child)
                    elif gc.type == "class_definition":
                        # Let the class handler pick it up with decorators
                        name_node = gc.child_by_field_name("name")
                        if name_node is None:
                            continue
                        name = self._node_text(name_node, source)
                        line = gc.start_point[0] + 1
                        bases_node = gc.child_by_field_name("superclasses")
                        parent_class = None
                        conformances_list = []
                        if bases_node:
                            base_names = []
                            for n in bases_node.children:
                                if n.type in ("identifier", "attribute"):
                                    base_names.append(self._node_text(n, source))
                            if base_names:
                                parent_class = base_names[0]
                                conformances_list = base_names[1:]
                        decorators = self._collect_python_decorators(child, source)
                        symbols.append(SymbolInfo(
                            file_path=rel_path,
                            symbol_type="class",
                            symbol_name=name,
                            line_number=line,
                            end_line=gc.end_point[0] + 1,
                            parent_symbol=parent,
                            parent_class=parent_class,
                            conformances=", ".join(conformances_list) if conformances_list else None,
                            imports=imports,
                            decorators=decorators,
                        ))
                        body = gc.child_by_field_name("body")
                        if body:
                            self._walk_python_node(body, source, rel_path, imports, symbols, parent=name, depth=depth + 1)

    def _add_python_func(self, node, source, rel_path, imports, symbols, parent, decorators_from=None):
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return
        name = self._node_text(name_node, source)
        line = node.start_point[0] + 1

        # Return type
        return_type = None
        ret_node = node.child_by_field_name("return_type")
        if ret_node:
            return_type = self._node_text(ret_node, source).strip()

        # Params
        params_node = node.child_by_field_name("parameters")
        params_text = self._node_text(params_node, source) if params_node else ""

        # Async?
        is_async = any(n.type == "async" or self._node_text(n, source) == "async"
                       for n in node.children)

        # Signature
        signature = f"def {name}{params_text}"
        if return_type:
            signature += f" -> {return_type}"
        if is_async:
            signature = "async " + signature
        if len(signature) > 200:
            signature = signature[:200] + "..."

        # Decorators
        dec_source = decorators_from or node
        decorators = self._collect_python_decorators(dec_source, source)

        symbols.append(SymbolInfo(
            file_path=rel_path,
            symbol_type="func",
            symbol_name=name,
            line_number=line,
            end_line=node.end_point[0] + 1,
            signature=signature,
            parent_symbol=parent,
            return_type=return_type,
            imports=imports,
            decorators=decorators,
        ))

    def _collect_python_decorators(self, node, source: bytes) -> list[str]:
        """Collect decorator strings from a node's children."""
        decorators = []
        for child in node.children:
            if child.type == "decorator":
                decorators.append(self._node_text(child, source).strip())
        # Also check prev sibling for standalone decorators
        if not decorators:
            prev = node.prev_named_sibling
            while prev and prev.type == "decorator":
                decorators.insert(0, self._node_text(prev, source).strip())
                prev = prev.prev_named_sibling
        return decorators

    def _extract_python_imports(self, root, source: bytes) -> list[str]:
        """Extract top-level module names (not imported names)."""
        modules = []
        seen: set[str] = set()
        for child in root.children:
            if child.type == "import_statement":
                # import X, import X.Y.Z → X
                # import numpy as np → numpy  (strip alias)
                text = self._node_text(child, source).strip()
                for part in text.replace("import", "").split(","):
                    mod = part.strip().split(" as ")[0].strip().split(".")[0]
                    if mod and mod not in seen and not mod.startswith("_"):
                        modules.append(mod)
                        seen.add(mod)
            elif child.type == "import_from_statement":
                # from X.Y import A, B → X  (skip relative: from . import X)
                text = self._node_text(child, source).strip()
                m = re.match(r'from\s+([\w.]+)\s+import', text)
                if m:
                    mod = m.group(1).lstrip(".").split(".")[0]
                    if mod and mod not in seen and not mod.startswith("_"):
                        modules.append(mod)
                        seen.add(mod)
        return modules[:30]

    # ── TypeScript / JavaScript ───────────────────────────────────────────────
    def _extract_typescript(self, tree, source: bytes, rel_path: str, language) -> list[SymbolInfo]:
        symbols: list[SymbolInfo] = []
        root = tree.root_node
        imports = self._extract_ts_imports(root, source)
        self._walk_ts_node(root, source, rel_path, imports, symbols, parent=None)
        return symbols

    def _walk_ts_node(self, node, source, rel_path, imports, symbols, parent):
        ts_type_map = {
            "class_declaration":      "class",
            "interface_declaration":  "interface",
            "type_alias_declaration": "type",
            "enum_declaration":       "enum",
        }
        for child in node.children:
            ctype = child.type
            if ctype in ts_type_map:
                name_node = child.child_by_field_name("name")
                if name_node is None:
                    continue
                name = self._node_text(name_node, source)
                line = child.start_point[0] + 1

                # Heritage (extends/implements)
                parent_class = None
                conformances_list = []
                for n in child.children:
                    ntype = n.type
                    if "heritage" in ntype or "extends" in ntype:
                        ext_text = self._node_text(n, source)
                        if "extends" in ext_text:
                            parent_class = ext_text.replace("extends", "").strip().split(",")[0].strip()
                    if "implements" in ntype:
                        impl_text = self._node_text(n, source).replace("implements", "").strip()
                        conformances_list = [p.strip() for p in impl_text.split(",") if p.strip()]

                symbols.append(SymbolInfo(
                    file_path=rel_path,
                    symbol_type=ts_type_map[ctype],
                    symbol_name=name,
                    line_number=line,
                    end_line=child.end_point[0] + 1,
                    parent_symbol=parent,
                    parent_class=parent_class,
                    conformances=", ".join(conformances_list) if conformances_list else None,
                    imports=imports,
                ))
                # Recurse for methods
                body = child.child_by_field_name("body")
                if body:
                    self._walk_ts_node(body, source, rel_path, imports, symbols, parent=name)

            elif ctype in ("function_declaration", "method_definition"):
                name_node = child.child_by_field_name("name")
                if name_node is None:
                    continue
                name = self._node_text(name_node, source)
                line = child.start_point[0] + 1
                ret_node = child.child_by_field_name("return_type")
                return_type = self._node_text(ret_node, source).lstrip(":").strip() if ret_node else None

                first_line = self._node_text(child, source).split("{")[0].strip()
                signature = first_line[:200]

                symbols.append(SymbolInfo(
                    file_path=rel_path,
                    symbol_type="func",
                    symbol_name=name,
                    line_number=line,
                    end_line=child.end_point[0] + 1,
                    signature=signature,
                    parent_symbol=parent,
                    return_type=return_type,
                    imports=imports,
                ))

            elif ctype == "export_statement":
                # export class Foo / export function bar
                self._walk_ts_node(child, source, rel_path, imports, symbols, parent)

            else:
                # Recurse into program/statement_block etc
                if child.child_count > 0 and ctype in ("program", "statement_block"):
                    self._walk_ts_node(child, source, rel_path, imports, symbols, parent)

    def _extract_ts_imports(self, root, source: bytes) -> list[str]:
        """Extract package names from TS/JS import statements."""
        modules: list[str] = []
        seen: set[str] = set()
        for child in root.children:
            if child.type == "import_statement":
                text = self._node_text(child, source).strip()
                # Extract the module specifier from: import ... from 'pkg'  OR  import 'pkg'
                m = re.search(r"""from\s+['"]([^'"]+)['"]""", text)
                if not m:
                    m = re.search(r"""import\s+['"]([^'"]+)['"]""", text)
                if m:
                    spec = m.group(1)
                    # '@scope/pkg' → '@scope/pkg', 'next/dist/...' → 'next', 'react' → 'react'
                    if spec.startswith("@"):
                        pkg = "/".join(spec.split("/")[:2])
                    else:
                        pkg = spec.split("/")[0]
                    if pkg and pkg not in seen and not pkg.startswith("."):
                        modules.append(pkg)
                        seen.add(pkg)
        return modules[:20]

    # ── Kotlin ────────────────────────────────────────────────────────────────
    def _extract_kotlin(self, tree, source: bytes, rel_path: str, language) -> list[SymbolInfo]:
        symbols: list[SymbolInfo] = []
        root = tree.root_node
        imports = [self._node_text(c, source) for c in root.children if c.type == "import_header"][:20]
        self._walk_kotlin_node(root, source, rel_path, imports, symbols, parent=None)
        return symbols

    def _walk_kotlin_node(self, node, source, rel_path, imports, symbols, parent):
        kt_type_map = {
            "class_declaration":     "class",
            "object_declaration":    "class",
            "interface_declaration": "interface",
        }
        for child in node.children:
            ctype = child.type
            if ctype in kt_type_map:
                name_node = child.child_by_field_name("name")
                if name_node is None:
                    for c in child.children:
                        if c.type == "simple_identifier":
                            name_node = c
                            break
                if name_node:
                    symbols.append(SymbolInfo(
                        file_path=rel_path,
                        symbol_type=kt_type_map[ctype],
                        symbol_name=self._node_text(name_node, source),
                        line_number=child.start_point[0] + 1,
                        end_line=child.end_point[0] + 1,
                        parent_symbol=parent,
                        imports=imports,
                    ))
                    body = child.child_by_field_name("body")
                    if body:
                        self._walk_kotlin_node(body, source, rel_path, imports, symbols,
                                               parent=self._node_text(name_node, source))
            elif ctype == "function_declaration":
                name_node = child.child_by_field_name("name")
                if name_node is None:
                    for c in child.children:
                        if c.type == "simple_identifier":
                            name_node = c
                            break
                if name_node:
                    symbols.append(SymbolInfo(
                        file_path=rel_path,
                        symbol_type="func",
                        symbol_name=self._node_text(name_node, source),
                        line_number=child.start_point[0] + 1,
                        end_line=child.end_point[0] + 1,
                        parent_symbol=parent,
                        imports=imports,
                    ))

    # ── Go ────────────────────────────────────────────────────────────────────
    def _extract_go(self, tree, source: bytes, rel_path: str, language) -> list[SymbolInfo]:
        symbols: list[SymbolInfo] = []
        root = tree.root_node
        imports = []
        for child in root.children:
            if child.type == "import_declaration":
                imports.append(self._node_text(child, source).strip())
            elif child.type == "type_declaration":
                for spec in child.children:
                    if spec.type == "type_spec":
                        name_node = spec.child_by_field_name("name")
                        if name_node:
                            # Determine if struct or interface
                            sym_type = "struct"
                            type_node = spec.child_by_field_name("type")
                            if type_node and type_node.type == "interface_type":
                                sym_type = "interface"
                            symbols.append(SymbolInfo(
                                file_path=rel_path,
                                symbol_type=sym_type,
                                symbol_name=self._node_text(name_node, source),
                                line_number=spec.start_point[0] + 1,
                                end_line=spec.end_point[0] + 1,
                                imports=imports,
                            ))
            elif child.type == "function_declaration":
                name_node = child.child_by_field_name("name")
                if name_node:
                    symbols.append(SymbolInfo(
                        file_path=rel_path,
                        symbol_type="func",
                        symbol_name=self._node_text(name_node, source),
                        line_number=child.start_point[0] + 1,
                        end_line=child.end_point[0] + 1,
                        imports=imports,
                    ))
            elif child.type == "method_declaration":
                name_node = child.child_by_field_name("name")
                if name_node:
                    symbols.append(SymbolInfo(
                        file_path=rel_path,
                        symbol_type="func",
                        symbol_name=self._node_text(name_node, source),
                        line_number=child.start_point[0] + 1,
                        end_line=child.end_point[0] + 1,
                        imports=imports,
                    ))
        return symbols


# ── Singleton extractor ───────────────────────────────────────────────────────
_extractor = TreeSitterExtractor()


# ── build_symbol_index ────────────────────────────────────────────────────────
async def build_symbol_index(folder_path: str, user_id: str) -> int:
    """Scan folder with tree-sitter, write to symbol_index_v2 + symbol_index (compat)."""
    root = Path(folder_path).expanduser().resolve()
    if not root.exists():
        return 0

    logger.info("Symbol index: scanning %s for user %s", root, user_id)

    # Clear existing entries
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
            # Write to symbol_index_v2 (rich)
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
            # Write flat row to symbol_index (backward compat for inject_symbol_refs)
            await db.execute(
                """INSERT OR IGNORE INTO symbol_index
                   (user_id, project_path, file_path, symbol_type, symbol_name, line_number)
                   VALUES (?,?,?,?,?,?)""",
                (user_id, str(root), sym.file_path, sym.symbol_type, sym.symbol_name, sym.line_number),
            )
        await db.commit()

    logger.info("symbol_index_v2: %d symbols indexed from %s", len(all_symbols), root)
    return len(all_symbols)


# ── inject_symbol_refs (preserved from original, queries symbol_index) ────────
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

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # ── Pass 0: directory name matching ─────────────────────────────────
        # dir_map: stem_lower -> [rel_path, ...]  (ALL matching paths, not first-wins)
        dir_map: dict[str, list[str]] = {}

        def _dir_map_add(key: str, rel: str) -> None:
            lst = dir_map.setdefault(key, [])
            if rel not in lst:
                lst.append(rel)

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
                _dir_map_add(dname.lower(), rel)

        # Filesystem scan for non-code dirs AND script files not in symbol_index
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
                # Index script/config files by stem so "setup" → setup.sh, setup.py etc.
                for fname in filenames:
                    fp = Path(fname)
                    if fp.suffix.lower() in _SCRIPT_EXTS:
                        stem = fp.stem.lower()
                        if len(stem) >= 4 and not stem.startswith('.'):
                            rel_file = str(rel_p / fname) if str(rel_p) != "." else fname
                            _dir_map_add(stem, rel_file)

        # Pass 0 directory matching runs LAST (after symbol passes) so class names
        # like "backend service" → BackendService aren't stolen by directory tokens.

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
            all_symbols_db = [dict(r) for r in await cursor.fetchall()]

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

        # ── Pass 0: directory matching (runs last — only on uncovered tokens) ─
        if dir_map:
            def _dir_score(token: str, dname_lower: str) -> float:
                if dname_lower.startswith(token) and len(token) >= 5:
                    return 0.95
                # Prefix bonus only if token isn't much longer than dir name
                # (prevents "setupdosyasında".startswith("setup") false positive)
                if token.startswith(dname_lower) and len(dname_lower) >= 5:
                    if len(token) <= len(dname_lower) * 1.4:
                        return 0.90
                return jellyfish.jaro_winkler_similarity(token, dname_lower)

            def _best_dir(token: str) -> tuple[float, list[str]]:
                """Return (best_score, all_rels_for_best_key).
                When multiple paths share the same stem key, all are returned."""
                best_score, best_rels = 0.0, []
                for dname_lower, rels in dir_map.items():
                    s = _dir_score(token, dname_lower)
                    if s > best_score:
                        best_score, best_rels = s, rels
                return best_score, best_rels

            def _fmt_refs(rels: list[str]) -> str:
                """Format a list of paths as '@path1 @path2 ...'"""
                return " ".join(f"@{r}" for r in sorted(set(rels)))

            i = 0
            while i < len(words):
                if i in covered:
                    i += 1
                    continue
                matched = False
                if i + 1 < len(words) and (i + 1) not in covered:
                    bigram = (_clean_word(words[i]) + _clean_word(words[i + 1])).lower()
                    # Bigram must be close in length to the matched dir name (prevents
                    # "setupdosyasında" matching "setup/" via JW prefix bonus)
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


# ── lookup_symbol (updated to use symbol_index_v2) ───────────────────────────
async def lookup_symbol(query: str, user_id: str, limit: int = 5) -> list[dict]:
    """Fuzzy symbol lookup from symbol_index_v2. Returns enriched results."""
    query = query.strip()
    if not query:
        return []

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Exact match (case-insensitive)
        async with db.execute(
            """SELECT symbol_name, symbol_type, file_path, line_number,
                      end_line, signature, parent_symbol, parent_class,
                      conformances, return_type
               FROM symbol_index_v2
               WHERE user_id = ? AND LOWER(symbol_name) = LOWER(?)
               ORDER BY CASE symbol_type WHEN 'class' THEN 0 WHEN 'struct' THEN 1 WHEN 'protocol' THEN 2 ELSE 3 END
               LIMIT ?""",
            (user_id, query, limit),
        ) as cursor:
            rows = [dict(r) for r in await cursor.fetchall()]

        if rows:
            return rows

        # Prefix match
        async with db.execute(
            """SELECT symbol_name, symbol_type, file_path, line_number,
                      end_line, signature, parent_symbol, parent_class,
                      conformances, return_type
               FROM symbol_index_v2
               WHERE user_id = ? AND LOWER(symbol_name) LIKE LOWER(?)
               ORDER BY length(symbol_name)
               LIMIT ?""",
            (user_id, f"{query}%", limit),
        ) as cursor:
            rows = [dict(r) for r in await cursor.fetchall()]

        if rows:
            return rows

        # Substring match
        async with db.execute(
            """SELECT symbol_name, symbol_type, file_path, line_number,
                      end_line, signature, parent_symbol, parent_class,
                      conformances, return_type
               FROM symbol_index_v2
               WHERE user_id = ? AND LOWER(symbol_name) LIKE LOWER(?)
               ORDER BY length(symbol_name)
               LIMIT ?""",
            (user_id, f"%{query}%", limit),
        ) as cursor:
            return [dict(r) for r in await cursor.fetchall()]


# ── generate_project_notes ────────────────────────────────────────────────────
async def generate_project_notes(folder_path: str, user_id: str) -> str:
    """Generate .claude/project-notes.md from symbol_index_v2."""
    from datetime import datetime

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

    # Categorize
    by_type: dict[str, list] = {}
    for r in rows:
        by_type.setdefault(r["symbol_type"], []).append(r)

    # Language distribution
    lang_counts: dict[str, int] = {}
    for r in rows:
        ext = Path(r["file_path"]).suffix.lower()
        lang = _LANGUAGE_MAP.get(ext, ext)
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
    lang_str = ", ".join(f"{lang} ({cnt})" for lang, cnt in sorted(lang_counts.items()))

    # Pattern detection
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

    # Libraries — collect unique top-level module names from imports column
    # imports column already stores clean module names (fixed in _extract_python_imports)
    # For Swift, imports column stores bare module names like "Foundation", "SwiftUI"
    all_imports: set[str] = set()
    _noise = {"re", "os", "sys", "io", "abc", "json", "time", "math", "copy",
              "typing", "types", "enum", "uuid", "datetime", "pathlib", "logging",
              "functools", "itertools", "collections", "dataclasses", "contextlib",
              "asyncio", "inspect", "hashlib", "struct", "base64", "threading",
              # stdlib additions
              "gc", "queue", "concurrent", "subprocess", "socket", "signal",
              "traceback", "warnings", "weakref", "shutil", "tempfile", "glob",
              # voiceflow internal packages (relative imports land here)
              "api", "audio", "auth", "core", "db", "services", "transcription",
              "correction", "context"}
    for r in rows:
        if r["imports"]:
            try:
                imps = json.loads(r["imports"])
                for imp in imps:
                    # Already a clean module name (string, not full import statement)
                    mod = imp.strip().split(".")[0]
                    if (mod and len(mod) > 1 and not mod.startswith("_")
                            and mod not in _noise and mod[0].isalpha()):
                        all_imports.add(mod)
            except Exception:
                pass

    # Generate markdown
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

    # Key symbols (those with parent_class or conformances)
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

    # Repositories/Services detail
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

    # Write
    notes_path = root / ".claude" / "project-notes.md"
    notes_path.parent.mkdir(parents=True, exist_ok=True)
    notes_path.write_text(content, encoding="utf-8")
    logger.info("project-notes.md written: %s (%d bytes)", notes_path, len(content))
    return str(notes_path)
