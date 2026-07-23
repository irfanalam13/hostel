"""Liveness / readiness. Mirrors the Django /health/ convention."""
import httpx
from fastapi import APIRouter

from ..config import settings

router = APIRouter()


@router.get("/health/")
async def health():
    return {"status": "ok", "service": settings.SERVICE_NAME, "provider": settings.PROVIDER}


@router.get("/health/provider/")
async def health_provider():
    """Best-effort reachability check for the configured LLM backend."""
    if settings.PROVIDER != "ollama":
        return {"provider": settings.PROVIDER, "reachable": None, "detail": "no probe"}
    try:
        async with httpx.AsyncClient(base_url=settings.OLLAMA_URL, timeout=3.0) as c:
            r = await c.get("/api/tags")
            r.raise_for_status()
            models = [m.get("name") for m in r.json().get("models", [])]
        return {"provider": "ollama", "reachable": True, "models": models}
    except Exception as exc:
        return {"provider": "ollama", "reachable": False, "detail": str(exc)}
