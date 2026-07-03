import os
from rank_bm25 import BM25Okapi
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY"),
)


def tokenize(text: str) -> list[str]:
    return text.lower().split()


def bm25_search(
    query:    str,
    repo_url: str,
    top_k:    int = 15,
) -> list[dict]:
    result = (
        supabase.table("chunks")
        .select("id, file_path, function_name, language, start_line, end_line, content, summary")
        .eq("repo_url", repo_url)
        .execute()
    )
    chunks = result.data or []
    if not chunks:
        return []

    corpus = [
        tokenize(f"{c['function_name']} {c.get('summary', '')} {c['content']}")
        for c in chunks
    ]
    bm25   = BM25Okapi(corpus)
    scores = bm25.get_scores(tokenize(query))

    for i, chunk in enumerate(chunks):
        chunk["bm25_score"] = float(scores[i])

    ranked = sorted(chunks, key=lambda x: x["bm25_score"], reverse=True)
    return ranked[:top_k]
