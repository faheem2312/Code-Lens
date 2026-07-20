import hashlib


def compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def build_embed_text(chunk: dict, summary: str) -> str:
    parent = chunk.get("parent_symbol", "")
    calls = ", ".join(chunk.get("called_symbols", []))
    
    parts = [
        f"File: {chunk['file_path']}",
        f"Function: {chunk['function_name']}",
    ]
    if parent:
        parts.append(f"Parent Scope: {parent}")
    if calls:
        parts.append(f"Calls: {calls}")
    parts.extend([
        f"Language: {chunk['language']}",
        f"Summary: {summary}\n",
        chunk['content']
    ])
    return "\n".join(parts)


def enrich_chunk(chunk: dict, repo_url: str) -> dict:
    # No Gemini call — saves all quota for user queries
    summary   = f"Function {chunk['function_name']} in {chunk['file_path']}"
    file_hash = compute_hash(chunk["content"])
    embed_text = build_embed_text(chunk, summary)

    return {
        **chunk,
        "summary":    summary,
        "file_hash":  file_hash,
        "repo_url":   repo_url,
        "embed_text": embed_text,
    }
