from fastapi import APIRouter, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, Header
from typing import Optional
import asyncio
import os
from datetime import datetime
from src.api.models import (
    IngestRequest, IngestResponse,
    QueryRequest, QueryResponse,
    HealthResponse, ChunkSource,
    UserRegister, UserLogin, TokenResponse, UserProfile,
    CheckoutRequest, CheckoutResponse,
)
from src.ingestion.indexer import index_repository
from src.query import query_codelens
from src.api.auth import user_manager, create_access_token, verify_token
from src.api.billing import create_checkout_session

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(status="healthy", timestamp=datetime.utcnow())


@router.post("/auth/register", response_model=TokenResponse)
def register_user(request: UserRegister):
    try:
        user = user_manager.register_user(request.email, request.password, request.full_name or "")
        token = create_access_token({"sub": user["email"], "user_id": user["user_id"], "tier": user["tier"]})
        return TokenResponse(
            access_token=token,
            user_id=user["user_id"],
            email=user["email"],
            tier=user["tier"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/auth/login", response_model=TokenResponse)
def login_user(request: UserLogin):
    user = user_manager.authenticate_user(request.email, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    token = create_access_token({"sub": user["email"], "user_id": user["user_id"], "tier": user["tier"]})
    return TokenResponse(
        access_token=token,
        user_id=user["user_id"],
        email=user["email"],
        tier=user["tier"],
    )


@router.get("/auth/me", response_model=UserProfile)
def get_current_user(authorization: str = Header(..., description="Bearer token")):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format.")
    token = authorization.split(" ", 1)[1]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    
    user = user_manager.get_user(payload.get("sub", ""))
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
        
    return UserProfile(
        user_id=user["user_id"],
        email=user["email"],
        full_name=user.get("full_name", ""),
        tier=user.get("tier", "free"),
        repos_indexed=user.get("repos_indexed", 0),
        repo_limit=user.get("repo_limit", 3),
    )


@router.post("/billing/checkout", response_model=CheckoutResponse)
def checkout(request: CheckoutRequest, authorization: Optional[str] = Header(None)):
    user_id = "anonymous"
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
        payload = verify_token(token)
        if payload:
            user_id = payload.get("user_id", "anonymous")
            # Automatically upgrade user tier upon checkout in demo mode
            user_manager.update_tier(payload.get("sub", ""), request.tier)

    res = create_checkout_session(user_id=user_id, tier=request.tier, success_url=request.success_url, cancel_url=request.cancel_url)
    return CheckoutResponse(
        checkout_url=res["checkout_url"],
        session_id=res["session_id"],
    )


@router.websocket("/ws/ingest/logs")
async def websocket_ingest_logs(websocket: WebSocket, repo_url: str):
    """
    WebSocket endpoint for real-time streaming of repository ingestion logs.
    """
    await websocket.accept()
    from src.ingestion.indexer import task_manager
    last_log_index = 0

    try:
        while True:
            info = task_manager.get_task_info(repo_url)
            if info:
                logs = info.get("logs", [])
                status = info.get("status", "processing")
                if len(logs) > last_log_index:
                    new_logs = logs[last_log_index:]
                    last_log_index = len(logs)
                    await websocket.send_json({"logs": new_logs, "status": status})
                if status in ("completed", "failed", "cancelled"):
                    break
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass


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
            message="Indexing started — check logs for progress",
            repo_url=request.repo_url,
            status="processing",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ingest/logs")
def get_ingest_logs(repo_url: str):
    """
    Get the real-time logs and status of an active ingestion task.
    """
    from src.ingestion.indexer import task_manager
    info = task_manager.get_task_info(repo_url)
    if not info:
        return {"status": "not_started", "logs": ["No active indexing task found for this repository."]}
    return info


@router.post("/ingest/cancel")
def cancel_ingest(repo_url: str):
    """
    Cancel an active ingestion task.
    """
    from src.ingestion.indexer import task_manager
    task_manager.cancel_task(repo_url)
    return {"message": "Cancellation request submitted", "repo_url": repo_url}


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
