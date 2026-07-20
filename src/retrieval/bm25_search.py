import os
from supabase import create_client
from dotenv import load_dotenv
from src.utils import normalize_repo_url

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY"),
)


def bm25_search(
    query:    str,
    repo_url: str,
    top_k:    int = 15,
) -> list[dict]:
    """
    Perform a database-backed Full-Text Search (FTS) in Supabase.
    This replaces the in-memory BM25 search to avoid downloading all chunks.
    """
    if not query.strip():
        return []

    repo_url = normalize_repo_url(repo_url)

    # Clean query and wrap in double quotes to avoid PostgREST parsing errors (like commas)
    clean_query = query.replace('"', '')
    escaped_query = f'"{clean_query}"'

    try:
        # Match across content, function_name, and summary using OR conditions
        res = (
            supabase.table("chunks")
            .select("id, file_path, function_name, language, start_line, end_line, content, summary")
            .eq("repo_url", repo_url)
            .or_(f"content.wfts.{escaped_query},function_name.wfts.{escaped_query},summary.wfts.{escaped_query}")
            .limit(top_k)
            .execute()
        )
        chunks = res.data or []
        
        # Populate a dummy bm25_score for backward compatibility
        for i, chunk in enumerate(chunks):
            chunk["bm25_score"] = float(len(chunks) - i)
            
        return chunks
    except Exception as e:
        print(f"  ⚠️ Supabase FTS failed: {e}")
        return []

