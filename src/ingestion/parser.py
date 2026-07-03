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

SKIP_DIRS = {
    "node_modules", ".git", "venv", "__pycache__",
    ".venv", "dist", "build", ".next", "coverage",
}

FUNCTION_NODE_TYPES = {
    "function_definition",
    "function_declaration",
    "method_definition",
    "arrow_function",
}

MIN_FUNCTION_LINES = 2


def get_parser(extension: str) -> Parser | None:
    lang = LANGUAGE_MAP.get(extension)
    if not lang:
        return None
    parser = Parser()
    parser.language = lang     # ← 0.23.x API: set language after construction
    return parser


def extract_functions(file_path: str) -> list[dict]:
    path   = Path(file_path)
    ext    = path.suffix
    parser = get_parser(ext)

    if not parser:
        return []

    try:
        with open(file_path, "rb") as f:
            source = f.read()
    except (OSError, PermissionError):
        return []

    tree   = parser.parse(source)
    root   = tree.root_node
    chunks = []

    def traverse(node):
        if node.type in FUNCTION_NODE_TYPES:
            start = node.start_point[0]
            end   = node.end_point[0]

            if (end - start) < MIN_FUNCTION_LINES:
                for child in node.children:
                    traverse(child)
                return

            code      = source[node.start_byte:node.end_byte].decode("utf-8", errors="ignore")
            name_node = node.child_by_field_name("name")
            name      = name_node.text.decode("utf-8") if name_node else "anonymous"

            chunks.append({
                "file_path":     str(path),
                "function_name": name,
                "language":      ext.lstrip("."),
                "start_line":    start + 1,
                "end_line":      end   + 1,
                "content":       code,
            })

        for child in node.children:
            traverse(child)

    traverse(root)
    return chunks