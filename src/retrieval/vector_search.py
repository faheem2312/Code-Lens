import os
from dotenv import load_dotenv
from supabase import create_client
from src.ingestion.embedder import embed_single

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY"),
)


def vector_search(
    query:       str,
    repo_url:    str,
    match_count: int   = 15,
    threshold:   float = 0.4,
) -> list[dict]:
    query_vector = embed_single(query)
    result = supabase.rpc(
        "match_chunks",
        {
            "query_embedding":  query_vector,
            "match_threshold":  threshold,
            "match_count":      match_count,
            "repo_filter":      repo_url,
        },
    ).execute()
    return result.data or []
