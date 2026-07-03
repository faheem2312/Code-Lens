import os
import cohere
from dotenv import load_dotenv

load_dotenv()

co = cohere.Client(os.getenv("COHERE_API_KEY"))
RERANK_MODEL = "rerank-v4.0-pro"


def rerank(
    query:  str,
    chunks: list[dict],
    top_n:  int = 8,
) -> list[dict]:
    if not chunks:
        return []

    documents = [
        f"File: {c['file_path']}\n"
        f"Function: {c['function_name']}\n"
        f"Summary: {c.get('summary', '')}\n\n"
        f"{c['content']}"
        for c in chunks
    ]

    response = co.rerank(
        model=RERANK_MODEL,
        query=query,
        documents=documents,
        top_n=top_n,
    )

    reranked = []
    for hit in response.results:
        chunk = chunks[hit.index]
        chunk["rerank_score"] = round(hit.relevance_score, 4)
        reranked.append(chunk)

    return sorted(reranked, key=lambda x: x["rerank_score"], reverse=True)
