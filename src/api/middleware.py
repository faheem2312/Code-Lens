import time
from collections import defaultdict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

request_counts: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT      = 20
RATE_WINDOW_SEC = 60


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = now - RATE_WINDOW_SEC
        request_counts[client_ip] = [t for t in request_counts[client_ip] if t > window]
        if len(request_counts[client_ip]) >= RATE_LIMIT:
            raise HTTPException(status_code=429, detail="Rate limit exceeded.")
        request_counts[client_ip].append(now)
        return await call_next(request)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start    = time.time()
        response = await call_next(request)
        duration = int((time.time() - start) * 1000)
        print(f"[{request.method}] {request.url.path} -> {response.status_code} ({duration}ms)")
        return response
