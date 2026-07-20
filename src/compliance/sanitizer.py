import re

INJECTION_PATTERNS = [
    r"ignore (all |previous |above |system )*instructions",
    r"disregard (the |your |all |previous )*instructions",
    r"you are now", r"new persona", r"act as",
    r"forget everything", r"system prompt", r"jailbreak",
    r"pretend (you are|to be)", r"do anything now",
    r"<\|.*?\|>", r"\[INST\]", r"###\s*instruction",
    r"reveal (the |your )*(system prompt|initial instructions)",
    r"output (the |your )*(system prompt|instructions)",
    r"bypass (all |safety |content )*filters",
    r"dan mode", r"developer mode", r"override (system|safety)",
]

MAX_QUERY_LENGTH = 500


def sanitize_query(query: str) -> dict:
    flags = []

    if len(query) > MAX_QUERY_LENGTH:
        query = query[:MAX_QUERY_LENGTH]
        flags.append("TRUNCATED")

    lower = query.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, lower):
            flags.append("INJECTION_ATTEMPT")
            break

    query = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", query)
    query = re.sub(r"\s+", " ", query).strip()

    return {
        "clean_query": query,
        "flags":       flags,
        "flagged":     len(flags) > 0,
    }
