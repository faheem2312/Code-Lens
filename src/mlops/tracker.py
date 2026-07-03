import os
import mlflow
from dotenv import load_dotenv

load_dotenv()

mlflow.set_tracking_uri("mlruns")
mlflow.set_experiment("codelens-rag")


def log_query_run(
    question:      str,
    repo_url:      str,
    top_k:         int,
    latency_ms:    int,
    tokens:        int,
    num_chunks:    int,
    rerank_scores: list[float],
) -> None:
    try:
        with mlflow.start_run():
            mlflow.log_params({
                "repo_url":        repo_url,
                "top_k":           top_k,
                "embedding_model": os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-2"),
                "llm_model":       os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite"),
                "rerank_model":    "rerank-v4.0-pro",
            })
            mlflow.log_metrics({
                "latency_ms":       latency_ms,
                "tokens_used":      tokens,
                "chunks_retrieved": num_chunks,
                "top_rerank_score": max(rerank_scores) if rerank_scores else 0.0,
                "avg_rerank_score": sum(rerank_scores)/len(rerank_scores) if rerank_scores else 0.0,
            })
            mlflow.set_tags({
                "query_preview": question[:80],
                "environment":   os.getenv("ENVIRONMENT", "development"),
            })
    except Exception as e:
        print(f"  ⚠️ MLflow logging failed (non-critical): {e}")
