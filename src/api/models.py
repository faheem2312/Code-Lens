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
