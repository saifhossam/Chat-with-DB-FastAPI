"""Application entry point.

Example: run with `uvicorn app.main:app --reload`.
"""
from fastapi import FastAPI

from app.api import auth, chat, databases
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.database.connection import init_db

app = FastAPI(title=settings.app_name, version="1.0.0")
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