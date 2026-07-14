"""OpenAI-compatible chat backend.

Covers any provider that speaks the OpenAI `/chat/completions` protocol —
**Google Gemini** (via its OpenAI-compatibility layer), OpenAI, Groq, OpenRouter,
Together, etc. Streaming + tool-calling supported. The base URL and key come from
``settings.openai_compat`` so the same class serves every such provider.

Our neutral message shape (Ollama-style tool turns) is translated to strict
OpenAI form here — assistant tool-call turns get synthetic ids and the following
tool results are paired to them in order.
"""
import json
from typing import AsyncIterator

import httpx

from ..config import settings
from .base import Chunk, LLMProvider


def _to_openai_tools(tools: list[dict] | None) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("parameters", {"type": "object", "properties": {}}),
            },
        }
        for t in (tools or [])
    ]


def _to_openai_messages(messages: list[dict]) -> list[dict]:
    """Translate neutral messages to strict OpenAI format (tool ids paired)."""
    out: list[dict] = []
    pending_ids: list[str] = []
    for m in messages:
        role = m.get("role")
        if role == "assistant" and m.get("tool_calls"):
            pending_ids = []
            tcs = []
            for i, c in enumerate(m["tool_calls"]):
                cid = f"call_{len(out)}_{i}"
                pending_ids.append(cid)
                fn = c.get("function", c)
                args = fn.get("arguments", {})
                if not isinstance(args, str):
                    args = json.dumps(args)
                tcs.append(
                    {"id": cid, "type": "function", "function": {"name": fn.get("name", ""), "arguments": args}}
                )
            out.append({"role": "assistant", "content": m.get("content") or "", "tool_calls": tcs})
        elif role == "tool":
            cid = pending_ids.pop(0) if pending_ids else f"call_orphan_{len(out)}"
            out.append({"role": "tool", "tool_call_id": cid, "content": m.get("content", "")})
        else:
            out.append({"role": role, "content": m.get("content", "")})
    return out


class OpenAICompatProvider(LLMProvider):
    name = "openai"

    def __init__(self, model: str, base_url: str, api_key: str, temperature: float = 0.2, name: str | None = None):
        super().__init__(model=model, temperature=temperature)
        self.base_url = base_url
        self.api_key = api_key
        if name:
            self.name = name

    async def stream_chat(
        self, messages: list[dict], tools: list[dict] | None = None
    ) -> AsyncIterator[Chunk]:
        body = {
            "model": self.model,
            "messages": _to_openai_messages(messages),
            "stream": True,
            "temperature": self.temperature,
            "stream_options": {"include_usage": True},
        }
        if tools:
            body["tools"] = _to_openai_tools(tools)

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        tool_acc: dict[int, dict] = {}
        usage: dict = {}
        model_name = self.model

        async with httpx.AsyncClient(base_url=self.base_url, timeout=None) as client:
            async with client.stream("POST", "/chat/completions", json=body, headers=headers) as resp:
                if resp.status_code >= 400:
                    detail = (await resp.aread()).decode("utf-8", "ignore")[:300]
                    raise RuntimeError(f"LLM HTTP {resp.status_code}: {detail}")
                async for line in resp.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    model_name = obj.get("model", model_name)
                    if obj.get("usage"):
                        usage = obj["usage"]
                    for choice in obj.get("choices", []):
                        delta = choice.get("delta") or {}
                        if delta.get("content"):
                            yield Chunk(content=delta["content"])
                        for tc in delta.get("tool_calls") or []:
                            idx = tc.get("index", 0)
                            slot = tool_acc.setdefault(idx, {"name": "", "args": ""})
                            fn = tc.get("function") or {}
                            if fn.get("name"):
                                slot["name"] = fn["name"]
                            if fn.get("arguments"):
                                slot["args"] += fn["arguments"]

        tool_calls = []
        for idx in sorted(tool_acc):
            slot = tool_acc[idx]
            if not slot["name"]:
                continue
            try:
                args = json.loads(slot["args"]) if slot["args"] else {}
            except json.JSONDecodeError:
                args = {}
            tool_calls.append({"name": slot["name"], "arguments": args})

        yield Chunk(
            done=True,
            tool_calls=tool_calls,
            prompt_tokens=usage.get("prompt_tokens", 0) or 0,
            completion_tokens=usage.get("completion_tokens", 0) or 0,
            model=model_name,
        )
