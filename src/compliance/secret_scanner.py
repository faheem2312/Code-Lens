import re

SECRET_PATTERNS = [
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----", "[REDACTED_PRIVATE_KEY]"),
    (r"AKIA[0-9A-Z]{16}", "[REDACTED_AWS_KEY_ID]"),
    (r"AIza[0-9A-Za-z\-_]{35}", "[REDACTED_GEMINI_KEY]"),
    (r"sk-[a-zA-Z0-9]{32,}", "[REDACTED_OPENAI_KEY]"),
    (r"ghp_[a-zA-Z0-9]{36}", "[REDACTED_GITHUB_TOKEN]"),
    (r"glpat-[a-zA-Z0-9\-_]{20,}", "[REDACTED_GITLAB_TOKEN]"),
    (r"eyJ[a-zA-Z0-9_\-]{10,}\.eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}", "[REDACTED_JWT_TOKEN]"),
    (r"postgresql?://[^:]+:([^@]+)@", "[REDACTED_DB_PASSWORD]"),
]


def scan_and_redact_secrets(text: str) -> tuple[str, bool, list[str]]:
    """
    Scans text for hardcoded API keys, private keys, JWTs, and database passwords,
    returning (redacted_text, has_secrets, detected_types).
    """
    if not text:
        return text, False, []

    redacted = text
    detected = []

    for pattern, replacement in SECRET_PATTERNS:
        if re.search(pattern, redacted, flags=re.IGNORECASE):
            detected.append(replacement.strip("[]"))
            redacted = re.sub(pattern, replacement, redacted, flags=re.IGNORECASE)

    has_secrets = len(detected) > 0
    return redacted, has_secrets, detected
