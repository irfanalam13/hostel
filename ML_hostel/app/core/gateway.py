"""Async client for Django's AI gateway (apps.assistant).

This is the service's ONLY door to business data. Every call carries the
caller's context token, so Django re-checks tenancy + RBAC on each hop and the
assistant can never see more than the user could. Responses come back in the
platform's ``{success, data, ...}`` envelope, which we unwrap here.
"""
import httpx

from ..config import settings
from ..security import Context


class GatewayError(Exception):
    pass


def _unwrap(resp: httpx.Response) -> dict:
    resp.raise_for_status()
    payload = resp.json()
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


class Gateway:
    def __init__(self, ctx: Context):
        self.ctx = ctx
        self._client = httpx.AsyncClient(
            base_url=settings.DJANGO_API_URL,
            timeout=settings.TOOL_TIMEOUT,
            headers={"Authorization": f"Bearer {ctx.token}"},
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self._client.aclose()

    async def get_context(self) -> dict:
        """Recent conversation turns + workspace facts + allowed tool specs."""
        resp = await self._client.get(f"/ai/conversations/{self.ctx.conversation_id}/context/")
        return _unwrap(resp)

    async def run_tool(self, name: str, args: dict) -> dict:
        try:
            resp = await self._client.post(f"/ai/tools/{name}/", json=args or {})
            return _unwrap(resp)
        except httpx.HTTPStatusError as exc:
            # Surface a structured error the agent can hand back to the model
            # instead of crashing the stream.
            return {"tool": name, "error": f"{exc.response.status_code}: tool failed"}
        except httpx.HTTPError as exc:
            return {"tool": name, "error": str(exc)}

    async def complete(self, payload: dict) -> dict:
        resp = await self._client.post(
            f"/ai/conversations/{self.ctx.conversation_id}/complete/", json=payload
        )
        return _unwrap(resp)
