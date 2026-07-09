from fastapi import APIRouter, HTTPException, BackgroundTasks
from datetime import datetime
from src.api.models import (
    IngestRequest, IngestResponse,
    QueryRequest, QueryResponse,
    HealthResponse, ChunkSource,
)
from src.ingestion.indexer import index_repository
from src.query import query_codelens

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(status="healthy", timestamp=datetime.utcnow())


@router.post("/ingest", response_model=IngestResponse)
def ingest(request: IngestRequest, background_tasks: BackgroundTasks):
    """
    Clone a GitHub repo and index it into Supabase.
    Accepts either:
      - repo_url only (server clones it)
      - repo_path + repo_url (local path, for CLI use)
    """
    try:
        if request.repo_path and os.path.exists(request.repo_path):
            # Local path provided — index directly
            background_tasks.add_task(
                index_repository,
                request.repo_path,
                request.repo_url,
            )
        else:
            # No local path — clone from GitHub
            from src.ingestion.indexer import clone_and_index
            background_tasks.add_task(clone_and_index, request.repo_url)

        return IngestResponse(
            message="Indexing started — this takes a few minutes for large repos",
            repo_url=request.repo_url,
            status="processing",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    try:
        result = query_codelens(question=request.question, repo_url=request.repo_url, top_k=request.top_k)
        chunk_sources = [
            ChunkSource(
                file_path=c["file_path"],
                function_name=c["function_name"],
                start_line=c["start_line"],
                end_line=c["end_line"],
                rerank_score=c.get("rerank_score"),
            )
            for c in result["chunks"]
        ]
        return QueryResponse(
            answer=result["answer"], sources=result["sources"],
            chunks=chunk_sources, latency_ms=result["latency_ms"], tokens=result["tokens"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
