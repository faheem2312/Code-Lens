import os
import time
from dotenv import load_dotenv

from src.retrieval.hybrid        import hybrid_search
from src.retrieval.reranker      import rerank
from src.api.prompt              import build_system_prompt, build_user_prompt
from src.compliance.sanitizer    import sanitize_query
from src.compliance.audit_logger import log_audit_event
from src.gemini_client           import generate_text, generate_text_stream
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


def query_codelens_stream(
    question: str,
    repo_url: str,
    top_k:    int = 8,
):
    start = time.time()

    sanitized = sanitize_query(question)
    if "INJECTION_ATTEMPT" in sanitized["flags"]:
        raise ValueError("Query blocked: potential prompt injection detected.")
    question = sanitized["clean_query"]

    candidates = hybrid_search(question, repo_url, top_k=15)
    chunks     = rerank(question, candidates, top_n=top_k)

    system_prompt = build_system_prompt(chunks, repo_url)
    user_prompt   = build_user_prompt(question)

    file_paths = list({c["file_path"] for c in chunks})
    chunk_sources = [
        {
            "file_path": c["file_path"],
            "function_name": c.get("function_name"),
            "start_line": c.get("start_line", 0),
            "end_line": c.get("end_line", 0),
            "rerank_score": c.get("rerank_score"),
        }
        for c in chunks
    ]

    yield {
        "type": "metadata",
        "sources": file_paths,
        "chunks": chunk_sources,
    }

    full_answer = ""
    for token in generate_text_stream(system_prompt, user_prompt):
        full_answer += token
        yield {
            "type": "token",
            "token": token,
        }

    latency_ms = int((time.time() - start) * 1000)
    estimated_tokens = len(full_answer.split())

    log_audit_event({
        "event_type":  "query_stream",
        "query":       question,
        "response":    full_answer,
        "file_paths":  file_paths,
        "tokens_used": estimated_tokens,
        "latency_ms":  latency_ms,
        "flagged":     sanitized["flagged"],
        "flag_reason": ", ".join(sanitized["flags"]) if sanitized["flags"] else None,
    })

    log_query_run(
        question=question,
        repo_url=repo_url,
        top_k=top_k,
        latency_ms=latency_ms,
        tokens=estimated_tokens,
        num_chunks=len(chunks),
        rerank_scores=[c.get("rerank_score", 0.0) for c in chunks],
    )

    yield {
        "type": "done",
        "latency_ms": latency_ms,
        "tokens": estimated_tokens,
    }
