import re
from pathlib import Path
from tree_sitter import Language, Parser
import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript

PY_LANGUAGE = Language(tspython.language())
JS_LANGUAGE = Language(tsjavascript.language())

LANGUAGE_MAP = {
    ".py":  PY_LANGUAGE,
    ".js":  JS_LANGUAGE,
    ".ts":  JS_LANGUAGE,
}

SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".html", ".css", ".json", ".yaml", ".yml", ".toml", ".md",
    ".go", ".java", ".rs", ".cpp", ".c", ".h"
}

SKIP_DIRS = {
    "node_modules", ".git", "venv", "__pycache__",
    ".venv", "dist", "build", ".next", "coverage", ".pytest_cache",
}

FUNCTION_NODE_TYPES = {
    "function_definition",
    "function_declaration",
    "method_definition",
    "arrow_function",
}

CLASS_NODE_TYPES = {
    "class_definition",
    "class_declaration",
}

IMPORT_NODE_TYPES = {
    "import_statement",
    "import_from_statement",
}

MIN_CHUNK_LINES = 1


def get_parser(extension: str) -> Parser | None:
    lang = LANGUAGE_MAP.get(extension)
    if not lang:
        return None
    parser = Parser()
    parser.language = lang
    return parser


def extract_called_symbols(code: str) -> list[str]:
    """Extract symbol call names (e.g. store.New, jwt.GenerateToken, db.Query) from code snippet."""
    dot_calls = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*)\s*\(', code)
    direct_calls = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]{2,})\s*\(', code)
    
    keywords = {"if", "for", "while", "return", "switch", "func", "def", "class", "import", "type", "struct", "catch", "range", "len", "append", "make"}
    valid_direct = [c for c in direct_calls if c not in keywords]
    
    unique_symbols = sorted(list(set(dot_calls + valid_direct)))
    return unique_symbols[:10]


def parse_fallback_chunks(file_path: str, ext: str) -> list[dict]:
    """
    Fallback structural parser for HTML, CSS, Configs, Markdown, and non-tree-sitter languages.
    Splits content into logical sections or 40-line blocks.
    """
    path = Path(file_path)
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except (OSError, PermissionError):
        return []

    if not lines:
        return []

    chunks = []
    chunk_size = 40
    overlap = 5
    total_lines = len(lines)

    lang = ext.lstrip(".")

    for i in range(0, total_lines, chunk_size - overlap):
        chunk_lines = lines[i : i + chunk_size]
        if not chunk_lines:
            break

        start_line = i + 1
        end_line = min(i + chunk_size, total_lines)
        code = "".join(chunk_lines)

        # Infer section name
        if ext in {".html", ".htm"}:
            name = f"html-section (L{start_line}-{end_line})"
        elif ext in {".css"}:
            name = f"css-rules (L{start_line}-{end_line})"
        elif ext in {".json", ".yaml", ".yml", ".toml"}:
            name = f"config-block (L{start_line}-{end_line})"
        elif ext in {".md"}:
            name = f"doc-section (L{start_line}-{end_line})"
        else:
            name = f"code-block (L{start_line}-{end_line})"

        called = extract_called_symbols(code)

        chunks.append({
            "file_path":      str(path),
            "function_name":  name,
            "parent_symbol":  "",
            "called_symbols": called,
            "language":       lang,
            "start_line":     start_line,
            "end_line":       end_line,
            "content":        code,
        })

    return chunks


def extract_functions(file_path: str) -> list[dict]:
    """
    Extract logical chunks (functions, classes, imports, config blocks, HTML/CSS sections) from a file.
    Maintains function signature compatibility with existing pipeline.
    """
    path   = Path(file_path)
    ext    = path.suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        return []

    parser = get_parser(ext)

    # Use structural fallback for non-Tree-Sitter supported file types (HTML, CSS, JSON, YAML, Go, Rust, etc.)
    if not parser:
        return parse_fallback_chunks(file_path, ext)

    try:
        with open(file_path, "rb") as f:
            source = f.read()
    except (OSError, PermissionError):
        return []

    tree   = parser.parse(source)
    root   = tree.root_node
    chunks = []
    visited_bytes = set()

    def traverse(node, current_class=""):
        node_key = (node.start_byte, node.end_byte)

        # Track Class Parent Scope
        if node.type in CLASS_NODE_TYPES:
            name_node = node.child_by_field_name("name")
            class_name = name_node.text.decode("utf-8") if name_node else "AnonymousClass"
            current_class = f"class:{class_name}"

            if node_key not in visited_bytes:
                visited_bytes.add(node_key)
                start = node.start_point[0]
                end   = node.end_point[0]
                if (end - start) >= MIN_CHUNK_LINES:
                    code   = source[node.start_byte:node.end_byte].decode("utf-8", errors="ignore")
                    called = extract_called_symbols(code)
                    chunks.append({
                        "file_path":      str(path),
                        "function_name":  current_class,
                        "parent_symbol":  "",
                        "called_symbols": called,
                        "language":       ext.lstrip("."),
                        "start_line":     start + 1,
                        "end_line":       end   + 1,
                        "content":        code,
                    })

        # Parse Functions & Methods
        elif node.type in FUNCTION_NODE_TYPES and node_key not in visited_bytes:
            visited_bytes.add(node_key)
            start = node.start_point[0]
            end   = node.end_point[0]

            if (end - start) >= MIN_CHUNK_LINES:
                code      = source[node.start_byte:node.end_byte].decode("utf-8", errors="ignore")
                name_node = node.child_by_field_name("name")
                name      = name_node.text.decode("utf-8") if name_node else "anonymous"
                called    = extract_called_symbols(code)

                chunks.append({
                    "file_path":      str(path),
                    "function_name":  f"function:{name}",
                    "parent_symbol":  current_class,
                    "called_symbols": called,
                    "language":       ext.lstrip("."),
                    "start_line":     start + 1,
                    "end_line":       end   + 1,
                    "content":        code,
                })

        for child in node.children:
            traverse(child, current_class)

    traverse(root)

    # If no AST nodes were captured (e.g. script only contains module imports or top-level code), fall back to line chunking
    if not chunks:
        return parse_fallback_chunks(file_path, ext)

    return chunks