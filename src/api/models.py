from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class IngestRequest(BaseModel):
    repo_path: str = ""
    repo_url:  str

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=5, max_length=500)
    repo_url: str
    top_k:    int = Field(default=8, ge=1, le=20)

class ChunkSource(BaseModel):
    file_path:     str
    function_name: str
    start_line:    int
    end_line:      int
    rerank_score:  Optional[float] = None

class QueryResponse(BaseModel):
    answer:     str
    sources:    list[str]
    chunks:     list[ChunkSource]
    latency_ms: int
    tokens:     int

class IngestResponse(BaseModel):
    message:  str
    repo_url: str
    status:   str

class HealthResponse(BaseModel):
    status:    str
    timestamp: datetime
    version:   str = "1.0.0"
    models:    dict[str, str] = Field(
        default_factory=lambda: {
            "llm":       "gemini-3.1-flash-lite",
            "embedding": "gemini-embedding-2",
            "reranker":  "rerank-v4.0-pro",
        }
    )


class UserRegister(BaseModel):
    email: str
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = ""


class UserLogin(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    tier: str


class UserProfile(BaseModel):
    user_id: str
    email: str
    full_name: Optional[str] = ""
    tier: str = "free"
    repos_indexed: int = 0
    repo_limit: int = 3


class CheckoutRequest(BaseModel):
    tier: str = "pro"
    success_url: str = "http://127.0.0.1:8000/?subscription=success"
    cancel_url: str = "http://127.0.0.1:8000/?subscription=cancel"


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str
