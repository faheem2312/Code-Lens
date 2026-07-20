def build_system_prompt(chunks: list[dict], repo_url: str) -> str:
    context_blocks = []
    for i, chunk in enumerate(chunks, start=1):
        parent_info = f"\nParent   : {chunk['parent_symbol']}" if chunk.get('parent_symbol') else ""
        calls_info = f"\nCalls    : {', '.join(chunk['called_symbols'])}" if chunk.get('called_symbols') else ""
        
        block = (
            f"--- Chunk {i} ---\n"
            f"File     : {chunk['file_path']}\n"
            f"Function : {chunk['function_name']}{parent_info}{calls_info}\n"
            f"Language : {chunk['language']}\n"
            f"Lines    : {chunk['start_line']}-{chunk['end_line']}\n"
            f"Summary  : {chunk.get('summary', 'N/A')}\n\n"
            f"{chunk['content']}\n"
            f"--- End Chunk {i} ---"
        )
        context_blocks.append(block)

    context = "\n\n".join(context_blocks)

    return f"""You are CodeLens, an expert codebase assistant for: {repo_url}

STRICT RULES:
1. Answer using ONLY the code context provided below.
2. Always reference exact file path and function name.
3. Quote code snippets max 10 lines.
4. If answer is NOT in context, say: "I couldn't find that in the indexed codebase."
5. Never invent file paths or function names.

CONTEXT ({len(chunks)} chunks):
{context}
"""


def build_user_prompt(query: str) -> str:
    return (
        f"{query}\n\n"
        f"Cite exact file paths and function names in your answer."
    )
