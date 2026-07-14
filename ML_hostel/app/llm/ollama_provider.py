"""Ollama backend (default, self-hosted).

Talks to Ollama's ``/api/chat`` NDJSON stream and normalises it into ``Chunk``s.
Supports native tool-calling for models that advertise it (llama3.1/3.2,
qwen2.5, mistral-nemo, ...).
"""
import json
from typing import AsyncIterator

import httpx

from ..config import settings
from .base import Chunk, LLMProvider


def _to_ollama_tools(tools: list[dict] | None) -> list[dict]:
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


class OllamaProvider(LLMProvider):
    name = "ollama"

    async def stream_chat(
        self, messages: list[dict], tools: list[dict] | None = None
    ) -> AsyncIterator[Chunk]:
        body = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": self.temperature},
        }
        if tools:
            body["tools"] = _to_ollama_tools(tools)

        tool_calls: list[dict] = []
        model = self.model
        prompt_tokens = completion_tokens = 0

        async with httpx.AsyncClient(base_url=settings.OLLAMA_URL, timeout=None) as client:
            async with client.stream("POST", "/api/chat", json=body) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    line = line.strip()
                    if not line:
                        continue
                    obj = json.loads(line)
                    model = obj.get("model", model)
                    msg = obj.get("message") or {}

                    content = msg.get("content") or ""
                    if content:
                        yield Chunk(content=content)

                    for call in msg.get("tool_calls") or []:
                        fn = call.get("function") or {}
                        args = fn.get("arguments")
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except json.JSONDecodeError:
                                args = {}
                        tool_calls.append({"name": fn.get("name", ""), "arguments": args or {}})

                    if obj.get("done"):
                        prompt_tokens = obj.get("prompt_eval_count", 0) or 0
                        completion_tokens = obj.get("eval_count", 0) or 0
                        yield Chunk(
                            done=True,
                            tool_calls=tool_calls,
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                            model=model,
                        )
                        return
