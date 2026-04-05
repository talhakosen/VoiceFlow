"""symbol/extractor.py — Tree-sitter AST symbol extraction.

SymbolInfo dataclass + TreeSitterExtractor class with per-language parsers.
Supported: Swift, Python, TypeScript/TSX/JavaScript, Kotlin, Go.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Language map ───────────────────────────────────────────────────────────────
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


# ── SymbolInfo dataclass ───────────────────────────────────────────────────────
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


# ── TreeSitterExtractor ────────────────────────────────────────────────────────
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

    # ── Regex fallback for files where tree-sitter fails ──────────────────────
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

    # ── Swift ──────────────────────────────────────────────────────────────────
    def _extract_swift(self, tree, source: bytes, rel_path: str, language) -> list[SymbolInfo]:
        symbols: list[SymbolInfo] = []
        root = tree.root_node
        imports = self._extract_swift_imports(root, source)
        self._walk_swift_node(root, source, rel_path, imports, symbols, parent=None)
        return symbols

    def _walk_swift_node(self, node, source, rel_path, imports, symbols, parent):
        for child in node.children:
            ctype = child.type

            if ctype == "class_declaration":
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

                if parent_class is None:
                    node_text = self._node_text(child, source)
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
                self._walk_swift_methods(child, source, rel_path, imports, symbols, parent=name)

            elif ctype == "protocol_declaration":
                name_node = child.child_by_field_name("name")
                if name_node is None:
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

                for n in child.children:
                    if n.type == "protocol_body":
                        for gc in n.children:
                            if gc.type == "protocol_function_declaration":
                                self._add_swift_func(gc, source, rel_path, imports, symbols, parent=name)

            elif ctype == "function_declaration":
                self._add_swift_func(child, source, rel_path, imports, symbols, parent)

    def _walk_swift_methods(self, container, source, rel_path, imports, symbols, parent):
        body = container.child_by_field_name("body")
        if body is None:
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
        name = None
        for n in node.children:
            if n.type == "simple_identifier":
                name = self._node_text(n, source)
                break
        if name is None:
            return

        line = node.start_point[0] + 1

        return_type = None
        found_arrow = False
        for n in node.children:
            if self._node_text(n, source) == "->":
                found_arrow = True
                continue
            if found_arrow and n.type not in ("->", "func", "simple_identifier", "(", ")", "parameter", ","):
                return_type = self._node_text(n, source).strip()
                break

        full_text = self._node_text(node, source)
        signature = full_text.split("{")[0].strip()
        if len(signature) > 200:
            signature = signature[:200] + "..."

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

    # ── Python ─────────────────────────────────────────────────────────────────
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

                bases_node = child.child_by_field_name("superclasses")
                parent_class = None
                conformances_list = []
                if bases_node:
                    base_names = []
                    for n in bases_node.children:
                        if n.type == "identifier":
                            base_names.append(self._node_text(n, source))
                        elif n.type == "attribute":
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
                    end_line=child.end_point[0] + 1,
                    parent_symbol=parent,
                    parent_class=parent_class,
                    conformances=", ".join(conformances_list) if conformances_list else None,
                    imports=imports,
                    decorators=decorators,
                ))
                body = child.child_by_field_name("body")
                if body:
                    self._walk_python_node(body, source, rel_path, imports, symbols, parent=name, depth=depth + 1)

            elif child.type == "function_definition":
                self._add_python_func(child, source, rel_path, imports, symbols, parent)

            elif child.type == "decorated_definition":
                for gc in child.children:
                    if gc.type == "function_definition":
                        self._add_python_func(gc, source, rel_path, imports, symbols, parent,
                                              decorators_from=child)
                    elif gc.type == "class_definition":
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

        return_type = None
        ret_node = node.child_by_field_name("return_type")
        if ret_node:
            return_type = self._node_text(ret_node, source).strip()

        params_node = node.child_by_field_name("parameters")
        params_text = self._node_text(params_node, source) if params_node else ""

        is_async = any(n.type == "async" or self._node_text(n, source) == "async"
                       for n in node.children)

        signature = f"def {name}{params_text}"
        if return_type:
            signature += f" -> {return_type}"
        if is_async:
            signature = "async " + signature
        if len(signature) > 200:
            signature = signature[:200] + "..."

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
        decorators = []
        for child in node.children:
            if child.type == "decorator":
                decorators.append(self._node_text(child, source).strip())
        if not decorators:
            prev = node.prev_named_sibling
            while prev and prev.type == "decorator":
                decorators.insert(0, self._node_text(prev, source).strip())
                prev = prev.prev_named_sibling
        return decorators

    def _extract_python_imports(self, root, source: bytes) -> list[str]:
        modules = []
        seen: set[str] = set()
        for child in root.children:
            if child.type == "import_statement":
                text = self._node_text(child, source).strip()
                for part in text.replace("import", "").split(","):
                    mod = part.strip().split(" as ")[0].strip().split(".")[0]
                    if mod and mod not in seen and not mod.startswith("_"):
                        modules.append(mod)
                        seen.add(mod)
            elif child.type == "import_from_statement":
                text = self._node_text(child, source).strip()
                m = re.match(r'from\s+([\w.]+)\s+import', text)
                if m:
                    mod = m.group(1).lstrip(".").split(".")[0]
                    if mod and mod not in seen and not mod.startswith("_"):
                        modules.append(mod)
                        seen.add(mod)
        return modules[:30]

    # ── TypeScript / JavaScript ────────────────────────────────────────────────
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
                self._walk_ts_node(child, source, rel_path, imports, symbols, parent)

            else:
                if child.child_count > 0 and ctype in ("program", "statement_block"):
                    self._walk_ts_node(child, source, rel_path, imports, symbols, parent)

    def _extract_ts_imports(self, root, source: bytes) -> list[str]:
        modules: list[str] = []
        seen: set[str] = set()
        for child in root.children:
            if child.type == "import_statement":
                text = self._node_text(child, source).strip()
                m = re.search(r"""from\s+['"]([^'"]+)['"]""", text)
                if not m:
                    m = re.search(r"""import\s+['"]([^'"]+)['"]""", text)
                if m:
                    spec = m.group(1)
                    if spec.startswith("@"):
                        pkg = "/".join(spec.split("/")[:2])
                    else:
                        pkg = spec.split("/")[0]
                    if pkg and pkg not in seen and not pkg.startswith("."):
                        modules.append(pkg)
                        seen.add(pkg)
        return modules[:20]

    # ── Kotlin ─────────────────────────────────────────────────────────────────
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

    # ── Go ─────────────────────────────────────────────────────────────────────
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


# ── Singleton extractor ────────────────────────────────────────────────────────
_extractor = TreeSitterExtractor()
