from src.retrieval.vector_search import vector_search
from src.retrieval.bm25_search   import bm25_search

RRF_K = 60


def reciprocal_rank_fusion(
    vector_results: list[dict],
    bm25_results:   list[dict],
) -> list[dict]:
    scores:    dict[str, float] = {}
    chunk_map: dict[str, dict]  = {}

    for rank, chunk in enumerate(vector_results):
        cid = str(chunk["id"])
        scores[cid]    = scores.get(cid, 0.0) + 1.0 / (RRF_K + rank + 1)
        chunk_map[cid] = chunk

    for rank, chunk in enumerate(bm25_results):
        cid = str(chunk["id"])
        scores[cid]    = scores.get(cid, 0.0) + 1.0 / (RRF_K + rank + 1)
        chunk_map[cid] = chunk

    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    merged = []
    for cid in sorted_ids:
        chunk = chunk_map[cid]
        chunk["rrf_score"] = round(scores[cid], 6)
        merged.append(chunk)
    return merged


def hybrid_search(
    query:    str,
    repo_url: str,
    top_k:    int = 15,
) -> list[dict]:
    vector_results = vector_search(query, repo_url)
    bm25_results   = bm25_search(query, repo_url)
    fused          = reciprocal_rank_fusion(vector_results, bm25_results)
    return fused[:top_k]
