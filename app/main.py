"""Application entry point.

Example: run with `uvicorn app.main:app --reload`.
"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api import auth, chat, databases
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.database.connection import init_db
from app.middleware.rate_limiter import rate_limiter

app = FastAPI(title=settings.app_name, version="1.0.0")


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware. Skips /health endpoint."""
    # Skip rate limiting for health checks
    if request.url.path == "/health":
        return await call_next(request)
    
    # Extract user_id from Authorization header if present
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            from jose import jwt
            token = auth_header[7:]  # Remove "Bearer " prefix
            payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
            user_id = str(payload.get("sub", "unknown"))
        except Exception:
            user_id = "unknown"
    else:
        user_id = "unknown"
    
    # Check rate limit
    if not rate_limiter.is_allowed(user_id):
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": f"Rate limit exceeded: {rate_limiter.requests_per_period} requests per {rate_limiter.period_seconds} seconds"},
            headers={
                "Retry-After": str(rate_limiter.period_seconds),
            },
        )
    
    return await call_next(request)


app.include_router(auth.router, prefix="/api/v1")
app.include_router(databases.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
register_exception_handlers(app)


@app.on_event("startup")
def on_startup() -> None:
    """ينشئ الجداول لو مش موجودة (بديل بسيط للـ migrations)."""
    init_db()


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Lightweight readiness endpoint used by a load balancer."""
    return {"status": "ok"}