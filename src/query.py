import os
import time
from dotenv import load_dotenv

from src.retrieval.hybrid        import hybrid_search
from src.retrieval.reranker      import rerank
from src.api.prompt              import build_system_prompt, build_user_prompt
from src.compliance.sanitizer    import sanitize_query
from src.compliance.audit_logger import log_audit_event
from src.gemini_client           import generate_text
from src.mlops.tracker           import log_query_run

load_dotenv()


def query_codelens(
    question: str,
    repo_url: str,
    top_k:    int = 8,
) -> dict:
    start = time.time()

    sanitized = sanitize_query(question)
    if "INJECTION_ATTEMPT" in sanitized["flags"]:
        raise ValueError("Query blocked: potential prompt injection detected.")
    question = sanitized["clean_query"]

    candidates = hybrid_search(question, repo_url, top_k=15)
    chunks     = rerank(question, candidates, top_n=top_k)

    system_prompt = build_system_prompt(chunks, repo_url)
    user_prompt   = build_user_prompt(question)

    answer, tokens = generate_text(system_prompt, user_prompt)

    latency_ms = int((time.time() - start) * 1000)
    file_paths = list({c["file_path"] for c in chunks})

    log_audit_event({
        "event_type":  "query",
        "query":       question,
        "response":    answer,
        "file_paths":  file_paths,
        "tokens_used": tokens,
        "latency_ms":  latency_ms,
        "flagged":     sanitized["flagged"],
        "flag_reason": ", ".join(sanitized["flags"]) if sanitized["flags"] else None,
    })

    log_query_run(
        question=question,
        repo_url=repo_url,
        top_k=top_k,
        latency_ms=latency_ms,
        tokens=tokens,
        num_chunks=len(chunks),
        rerank_scores=[c.get("rerank_score", 0.0) for c in chunks],
    )

    return {
        "answer":     answer,
        "sources":    file_paths,
        "chunks":     chunks,
        "latency_ms": latency_ms,
        "tokens":     tokens,
    }
