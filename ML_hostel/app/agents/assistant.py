"""The general assistant agent: a streaming tool-calling loop.

Yields plain dict events the SSE layer serialises:
  {"type": "token", "delta": str}          incremental answer text
  {"type": "tool",  "name": str, "status": "running"|"done"}
  {"type": "final", "content": str, "tokens_prompt": int, ...}
  {"type": "error", "message": str}

Tenancy/RBAC are already enforced upstream (tools run through the Django
gateway with the caller's token), so this loop only orchestrates the model.
"""
import json
from typing import AsyncIterator

from ..config import settings
from ..core.gateway import Gateway
from ..llm.base import LLMProvider
from ..rag.embeddings import get_embedder
from .prompts import build_system_prompt


async def run_assistant(gateway: Gateway, provider: LLMProvider) -> AsyncIterator[dict]:
    try:
        ctx = await gateway.get_context()
    except Exception as exc:  # gateway/context failure — nothing to answer with
        yield {"type": "error", "message": f"Could not load conversation: {exc}"}
        return

    tool_specs = ctx.get("tools") or []
    messages: list[dict] = [{"role": "system", "content": build_system_prompt(ctx)}]
    messages += ctx.get("messages") or []

    answer = ""
    used_tools: list[dict] = []
    sources: list[dict] = []
    embedder = get_embedder()
    last = None

    for round_i in range(settings.MAX_TOOL_ROUNDS + 1):
        # On the final permitted round, drop tools to force a text answer and
        # avoid an unbounded tool loop.
        offer_tools = tool_specs if round_i < settings.MAX_TOOL_ROUNDS else None

        turn_text = ""
        tool_calls: list[dict] = []
        try:
            async for chunk in provider.stream_chat(messages, tools=offer_tools):
                if chunk.content:
                    turn_text += chunk.content
                    yield {"type": "token", "delta": chunk.content}
                if chunk.done:
                    last = chunk
                    tool_calls = chunk.tool_calls
        except Exception as exc:
            yield {"type": "error", "message": f"Model error: {exc}"}
            return

        if not tool_calls:
            answer += turn_text
            break

        # Record the assistant's tool-call turn, then run each tool and feed the
        # results back for the next round.
        messages.append(
            {
                "role": "assistant",
                "content": turn_text,
                "tool_calls": [
                    {"function": {"name": c["name"], "arguments": c.get("arguments", {})}}
                    for c in tool_calls
                ],
            }
        )
        for call in tool_calls:
            name = call["name"]
            args = call.get("arguments", {})
            yield {"type": "tool", "name": name, "status": "running"}

            # RAG: the LLM asks with a text query; we own the embedding model, so
            # we vectorise here and hand Django the query vector to rank against
            # its tenant-scoped chunk store.
            if name == "search_knowledge":
                try:
                    vec = (await embedder.embed([args.get("query", "")]))[0]
                    args = {**args, "embedding": vec, "top_k": settings.RAG_TOP_K}
                except Exception:
                    pass

            result = await gateway.run_tool(name, args)
            used_tools.append({"name": name, "arguments": {k: v for k, v in args.items() if k != "embedding"}})

            if name == "search_knowledge":
                for r in (result.get("result") or {}).get("results", []):
                    src = {"title": r.get("title"), "document_id": r.get("document_id")}
                    if src not in sources:
                        sources.append(src)

            yield {"type": "tool", "name": name, "status": "done"}
            messages.append(
                {
                    "role": "tool",
                    "tool_name": name,
                    "content": json.dumps(result.get("result", result)),
                }
            )

    yield {
        "type": "final",
        "content": answer,
        "provider": provider.name,
        "model": last.model if last else provider.model,
        "tokens_prompt": last.prompt_tokens if last else 0,
        "tokens_completion": last.completion_tokens if last else 0,
        "tool_calls": used_tools,
        "sources": sources,
    }
