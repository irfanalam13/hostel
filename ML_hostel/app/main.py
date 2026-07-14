"""FastAPI entrypoint for the ML_hostel AI service.

Run: ``uvicorn app.main:app --host 0.0.0.0 --port 9000``
"""
from fastapi import FastAPI

from .api import chat, health, knowledge
from .config import settings

app = FastAPI(
    title="ML_hostel — Hostel SaaS AI Service",
    version="0.1.0",
    description="AI orchestration service (chat assistant). All business data is "
    "reached through the Django gateway with the caller's context token.",
)

if settings.cors_enabled:
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

app.include_router(health.router, tags=["health"])
app.include_router(chat.router, tags=["chat"])
app.include_router(knowledge.router, tags=["knowledge"])


@app.get("/")
async def root():
    return {"service": settings.SERVICE_NAME, "status": "ok", "docs": "/docs"}
