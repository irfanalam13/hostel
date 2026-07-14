"""Streaming chat endpoint (Server-Sent Events).

SSE (not WebSockets) is deliberate: the platform runs on WSGI/Gunicorn with no
ASGI/Channels layer, and a one-way token stream is all chat needs. The browser
posts here with the context token it got from Django; on completion the service
writes the answer back through the gateway so Django stays the source of truth.
"""
import json
import time
from typing import AsyncIterator

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse, StreamingResponse

from ..agents.assistant import run_assistant
from ..core.gateway import Gateway
from ..llm.factory import get_provider
from ..security import InvalidContext, decode_context

router = APIRouter()


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _extract_token(authorization: str | None, request: Request) -> str | None:
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:].strip()
    # EventSource fallback (can't set headers): ?token=
    return request.query_params.get("token")


@router.post("/v1/chat/stream")
@router.get("/v1/chat/stream")
async def chat_stream(request: Request, authorization: str | None = Header(default=None)):
    token = _extract_token(authorization, request)
    if not token:
        return JSONResponse({"detail": "missing context token"}, status_code=401)
    try:
        ctx = decode_context(token)
    except InvalidContext as exc:
        return JSONResponse({"detail": str(exc)}, status_code=401)

    async def event_stream() -> AsyncIterator[str]:
        started = time.monotonic()
        final: dict | None = None
        gateway = Gateway(ctx)
        try:
            provider = get_provider()
            async for ev in run_assistant(gateway, provider):
                if ev["type"] == "final":
                    final = ev
                    continue
                yield _sse(ev["type"], ev)

            latency_ms = int((time.monotonic() - started) * 1000)
            if final is not None:
                payload = {
                    "content": final["content"],
                    "provider": final["provider"],
                    "model": final["model"],
                    "tokens_prompt": final["tokens_prompt"],
                    "tokens_completion": final["tokens_completion"],
                    "latency_ms": latency_ms,
                    "tool_calls": final["tool_calls"],
                    "sources": final.get("sources", []),
                }
                # Persist the answer + usage back in Django (source of truth).
                try:
                    await gateway.complete(payload)
                except Exception:
                    pass  # a persistence hiccup must not break the user's stream
                yield _sse("done", {**payload})
            else:
                yield _sse("done", {"content": "", "latency_ms": latency_ms})
        except Exception as exc:  # last-resort guard so the stream always closes
            yield _sse("error", {"message": str(exc)})
        finally:
            await gateway.__aexit__(None, None, None)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
