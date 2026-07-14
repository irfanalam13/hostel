# ML_hostel — AI service for the Hostel Management SaaS

`ML_hostel/` is the **only** home for AI/LLM logic in this platform. It runs as a
standalone **FastAPI microservice** alongside the Django backend and reuses the
existing platform for everything non-AI — multi-tenancy, RBAC, audit, and the
business data layer are **never** re-implemented here.

Phases done: **1 — Foundation + Chat Assistant** and **2 — RAG / Knowledge Base**
(tenant documents chunked + embedded so the assistant answers policy/rules
questions with citations). Later phases (more agents, forecasting/insights,
vision/OCR, voice) extend this same spine.

---

## Architecture

```
Browser (admin app · features/ai)
   │  1. POST /api/ai/chat/         (session cookie)
   ▼
Django BFF gateway — backend/apps/assistant
   • IsHostelResolved + ActionPermissions(ai.chat) + RequiresFeature("ai_chat")
   • monthly max_ai_requests quota · audit event
   • persists the user Message
   • mints a short-lived HS256 "context token" {tenant, user, role, perms, conv}
   │  returns { conversation_id, stream_url, token }
   ▼
Browser opens SSE  ──►  ML_hostel  (this service)
   • verifies the context token (shared HMAC secret)
   • runs the agent tool-calling loop over the configured LLM (Ollama by default)
   • for live data, calls BACK into Django's tool endpoints WITH the token, so
     tenancy + RBAC are re-checked on every hop
   • streams tokens over SSE; on completion writes the answer + usage back to
     Django (the single source of truth)
```

**Why a token, not a shared DB?** The service holds no business data and no DB
credentials. The token captures *who is asking and what they may see*, and every
data read goes through Django's real APIs — so the assistant can never surface
anything the signed-in user couldn't already access.

**Why SSE, not WebSockets?** The platform runs on WSGI/Gunicorn with no
ASGI/Channels layer. A one-way token stream is all chat needs, and SSE rides the
existing single-origin nginx gateway (`/ai`) with no new infrastructure.

---

## Layout

```
ML_hostel/
  app/
    main.py            FastAPI app (health + chat routers, CORS)
    config.py          env-driven settings (provider-agnostic)
    security.py        context-token verification (HS256, shared secret)
    core/gateway.py    async client for Django's AI gateway (the only data door)
    llm/               provider abstraction
      base.py            LLMProvider interface + Chunk
      ollama_provider.py Ollama backend (default, streaming + tools)
      factory.py         get_provider() — the single switch point
    agents/
      assistant.py       streaming tool-calling loop (+ RAG query embedding)
      prompts.py         role/tenant-aware system prompt (cites KB sources)
    rag/                 Phase 2
      chunking.py        paragraph-aware, budgeted chunks
      embeddings.py      Ollama embeddings (nomic-embed-text), provider-agnostic
    api/
      chat.py            POST/GET /v1/chat/stream  (SSE)
      knowledge.py       POST /v1/ingest, /v1/embed  (Phase 2)
      health.py          /health/ + /health/provider/
  tests/               token-verification + chunking tests
  Dockerfile           multi-stage (mirrors backend/Dockerfile)
  requirements.txt
  .env.example
```

## Configuration

All env vars are optional except `ML_SHARED_SECRET`, which **must match** the
Django backend's `ML_SHARED_SECRET`. See `.env.example`. Key ones:

| Var | Default | Notes |
|-----|---------|-------|
| `ML_SHARED_SECRET` | — | HMAC secret; must equal Django's. No fallback (fail closed). |
| `ML_PROVIDER` | `ollama` | `ollama` \| `openai` \| `azure` \| `anthropic` \| … |
| `ML_MODEL` | `llama3.2:3b` | model id for the provider |
| `ML_DJANGO_API_URL` | `http://web:8000/api` | service-internal gateway URL |
| `ML_OLLAMA_URL` | `http://ollama:11434` | Ollama runtime |
| `ML_MAX_TOOL_ROUNDS` | `4` | tool-call rounds before forcing an answer |

## Running (dev)

The service is wired into the root `docker-compose` stack (services `ollama` +
`ml_hostel`) and reached same-origin through the nginx gateway at `/ai`.

```bash
docker compose up -d ollama ml_hostel
# pull a model once (persisted in the ollama_data volume):
docker compose exec ollama ollama pull llama3.2:3b
curl http://localhost:9000/health/            # or http://localhost/ai/health/
```

Open the admin app → **AI Assistant** in the sidebar.

## Switching providers

Set `ML_PROVIDER` + the matching credentials — no code change. To add a new
backend, implement an `LLMProvider` subclass in `app/llm/` and wire it into
`app/llm/factory.py:get_provider`. The agent loop and SSE layer only see
`Chunk`s, so nothing upstream changes.

## Tests

```bash
cd ML_hostel && ML_SHARED_SECRET=test python -m pytest        # token verification
cd backend   && pytest apps/assistant/                        # gateway (11 tests)
```
