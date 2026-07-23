"""Provider-agnostic streaming chat interface.

Every provider yields the same ``Chunk`` shape, so the agent loop and the SSE
layer never learn which backend answered. Adding OpenAI/Azure/Anthropic/etc. is
a new ``LLMProvider`` subclass wired into ``factory.get_provider`` — no changes
anywhere upstream.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import AsyncIterator


@dataclass
class Chunk:
    content: str = ""                    # incremental text delta
    tool_calls: list[dict] = field(default_factory=list)  # [{name, arguments}]
    done: bool = False
    prompt_tokens: int = 0
    completion_tokens: int = 0
    model: str = ""


class LLMProvider:
    name = "base"

    def __init__(self, model: str, temperature: float = 0.2):
        self.model = model
        self.temperature = temperature

    async def stream_chat(
        self, messages: list[dict], tools: list[dict] | None = None
    ) -> AsyncIterator[Chunk]:  # pragma: no cover - interface
        raise NotImplementedError
        yield  # make this an async generator
