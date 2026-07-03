from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.middleware import RateLimitMiddleware, LoggingMiddleware
from src.api.routes import router

app = FastAPI(
    title="CodeLens API",
    description="AI-powered codebase Q&A — powered by Gemini (free tier)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.include_router(router, prefix="/api/v1")
