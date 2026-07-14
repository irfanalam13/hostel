# Master Implementation Prompt — Enterprise AI for the Hostel Management SaaS

> This is the **single source of truth** for building AI into this platform. It is
> written to be handed to an implementer (human or AI agent) and produce work that
> is indistinguishable from the existing codebase. It is **grounded in the real
> repository** — every pattern, file path, and constraint below was verified against
> the actual code, not assumed. Follow it literally.

---

## 0. Prime Directive

Extend the existing Hostel SaaS with AI. **Do NOT** build a standalone AI app,
duplicate business logic, or create parallel APIs. Reuse the platform's tenancy,
RBAC, audit, Celery, notifications, subscription gating, and data layer. All
AI/LLM logic lives **only** in `ML_hostel/`. The AI must feel like it was always
part of the product (Copilot / Einstein / Joule class), and remain fully
multi-tenant, secure, provider-agnostic, event-driven, and production-ready.

### Locked architectural decisions (do not revisit)
1. **Topology:** `ML_hostel/` is a **standalone FastAPI microservice**. The
   Django side gets a **thin BFF** (`backend/apps/assistant/`) that authorises,
   gates, audits, and proxies — it contains **no AI logic**.
2. **Data access:** the service reaches business data **only** by calling Django's
   own endpoints with a short-lived, HMAC-signed **context token** (tenant + user
   + the caller's resolved permissions). Tenancy + RBAC are enforced by Django on
   every hop. The service holds no DB credentials and no business data.
3. **Default provider:** **Ollama / self-hosted**, behind a provider-agnostic
   interface. Switching providers is config-only.
4. **Streaming:** **Server-Sent Events (SSE)**, not WebSockets — the platform is
   WSGI/Gunicorn with no ASGI/Channels layer. SSE rides the existing single-origin
   nginx gateway at `/ai`.
5. **RAG / vector store:** deferred until Phase 2 (see roadmap).

---

## 1. The codebase you are extending (verified facts)

**Backend** — Django 5.1 + DRF, `backend/`, ~30 apps under `backend/apps/`
(`students`, `admissions`, `rooms`, `fees`, `payments`, `finance`, `accounting`,
`inventory`, `staff`, `operations`, `complaints`, `notices`, `notifications`,
`analytics`, `auditlog`, `subscriptions`, `platformops`, `security`, `tenants`,
`dashboard`, `reports`, `exports`, `residents`, `billing`, `backups`, …).

**Frontend** — Next.js App Router monorepo, `frontend/apps/admin` (+ `apps/client`)
with `packages/@hostel/*` (`api`, `hooks`, `ui`, `auth`, `permissions`, `pwa`).

**Infra** — Docker Compose (`web` Gunicorn/WSGI, `celery_worker`, `celery_beat`,
`redis`, `postgres:16-alpine`, `frontend`, `admin`, dev `nginx` gateway, plus the
new `ollama` + `ml_hostel`). Prod = Vercel (frontend) + Render (backend).

### Patterns you MUST reuse (with exact anchors)

| Concern | Reuse this | Anchor |
|---|---|---|
| Tenancy (model) | `HostelScopedModel` (UUID pk, `hostel` FK) | `apps/common/models.py:12` |
| Tenancy (request) | `request.hostel` set by middleware; querysets filter `hostel=request.hostel`, writes `serializer.save(hostel=…)` | `apps/tenants/middleware.py` |
| Membership guard | `IsHostelResolved` (resolved hostel **and** membership) | `apps/common/permissions.py` |
| RBAC | `"module.action"` strings; `ActionPermissions` + `view.permission_map`; wildcards `*` / `module.*` | `apps/common/rbac.py` (`MODULES`, `FEATURE_PERMISSIONS`, `DEFAULT_ROLE_PERMISSIONS`) |
| Audit | `record_event(request, action=…, actor=…, hostel=…, entity_type=…, entity_id=…, message=…, meta=…)` → hash-chained | `apps/auditlog/services.py:59` |
| Plan gating | `RequiresFeature("ai_*")` permission + `enforce_limit(hostel, "max_ai_requests")`; `Entitlements(hostel).can_use/limit` | `apps/subscriptions/gates.py`, `.../catalog.py` |
| Async work | `@shared_task` in `apps/<name>/tasks.py` (auto-discovered); periodic via `CELERY_BEAT_SCHEDULE` | `config/celery.py`, `config/settings.py` |
| Notifications | `notifications.services.create_notification(...)` / `notifications.events.*` — never build a sender | `apps/notifications/services.py:286` |
| List filtering | DRF `search_fields` / `filterset_fields` / `ordering_fields` (global backends) | `config/settings.py` |
| Response shape | `StandardJSONRenderer` envelope `{success,message,data,meta}` | `apps/common/renderers.py` |
| FE feature | `features/<name>/{api/*.api.ts, components/(+primitives.tsx Shell), types/*.types.ts, registry.ts}` | `features/finance`, `features/inventory` |
| FE data | `apiFetch` (`@hostel/api`, cookie-native, CSRF, envelope-unwrap, single-flight) + `useApi` (`@hostel/hooks`) | `packages/api/src/apiClient.ts` |
| FE gating | add `PERMISSIONS` + `ROLE_GRANTS` + `ROUTE_POLICY` entry; nav in `Sidebar.tsx` + `CommandPalette.tsx` | `packages/permissions/src/*` |
| FE charts | `recharts` + CSS-var colors, `next/dynamic({ssr:false})` for heavy | `features/dashboard` |

### Real gaps you will introduce (they do NOT exist yet)
- **Streaming primitive** — none. Backend uses SSE via `StreamingResponse` in the
  service; frontend needs a raw `fetch` stream reader (built in Phase 1's
  `features/ai/api/ai.api.ts:streamChat` — reuse it).
- **Vector store** — Postgres has **no pgvector**. For RAG, swap the image to
  `pgvector/pgvector:pg16` + `CREATE EXTENSION vector` in a migration, **or** add
  an external vector service.
- **PDF** — WeasyPrint is installed (`backend/Dockerfile` has pango/cairo) but
  **unused**; wire it for AI reports.
- **Scheduled reports / cross-domain analytics service** — none; build in Phase 4.
- **`analytics` app is PWA telemetry only** — business forecasting must query the
  domain models directly, not `EventDailyRollup`.
- **No markdown renderer** on the frontend — add one (e.g. a sanitized renderer)
  for AI output when you leave plaintext.

---

## 2. Global, non-negotiable requirements (apply to EVERY phase)

- **Multi-tenancy:** every model is `HostelScopedModel`; every query filters by
  `request.hostel`; the service only ever acts within the token's `tid`. Never
  add a data path that could cross tenants. Add a cross-tenant isolation test.
- **RBAC:** register new permission strings in `apps/common/rbac.py` under the
  `ai` module (`ai.view`, `ai.chat`, `ai.reports`, `ai.manage` already exist).
  Gate every endpoint with `permission_map`. Never widen the token's claims.
- **Plan gating:** every AI surface sits behind an `ai_*` feature
  (`RequiresFeature`) and, where metered, `enforce_limit(hostel,"max_ai_requests")`.
- **Audit:** every AI action (chat, report, automation run, model change) calls
  `record_event(...)`.
- **Provider-agnostic:** all model calls go through `app/llm/base.py:LLMProvider`.
  New backends = a subclass wired into `app/llm/factory.py`. Nothing upstream
  changes.
- **Security:** verify the context token (fail closed); prompt-injection guarding
  on tool arguments; PII stays inside the tenant; no secrets in logs; rate-limit
  via the existing `apps/security` throttles.
- **Feature flags:** new/risky surfaces gated with `platformops.flags.is_enabled(...)`.
- **Tests:** backend pytest (mirror `apps/assistant/tests.py`), service pytest,
  frontend typecheck (`tsc --noEmit -p apps/admin`) must all pass.
- **Docs + memory:** update `ML_hostel/README.md` and the project memory per phase.

### RBAC permissions to use / add (`ai` module)
`ai.view` (see AI surfaces), `ai.chat` (use assistant), `ai.reports` (generate AI
reports/insights), `ai.manage` (models/prompts/providers/knowledge base/agents/
automation settings). Frontend coarse gate: `ai:view` in `packages/permissions`.

### Subscription features to use / add (`apps/subscriptions/catalog.py`)
Already seeded (BETA): `ai_dashboard`, `ai_chat`, `ai_reports`, `ai_assistant`,
limit `max_ai_requests`. Add per phase as needed: `ai_rag`, `ai_agents`,
`ai_forecasting`, `ai_vision`, `ai_voice`, `ai_automation`, and limits
`max_ai_tokens_month`, `max_ai_documents`.

---

## 3. `ML_hostel/` service — structure to grow into

Phase 1 exists. Keep this shape; add packages per phase, never a second AI root.

```
ML_hostel/app/
  main.py  config.py  security.py
  core/        gateway.py                 # Django BFF client (the only data door)
  llm/         base.py ollama_provider.py factory.py   (+ openai/azure/anthropic…)
  agents/      assistant.py prompts.py    (+ finance.py ops.py hr.py … per Phase 3)
  api/         chat.py health.py          (+ search.py reports.py voice.py …)
  rag/         (Phase 2) chunking.py embeddings.py vector_store.py retriever.py
  prediction/  (Phase 5) occupancy.py revenue.py recommendations.py
  vision/      (Phase 6) ocr.py
  speech/      (Phase 7) stt.py tts.py
  memory/      (Phase 3) summaries.py
```

The Django BFF (`backend/apps/assistant/`) grows matching endpoints
(`/api/ai/...`): tool endpoints (read-only, reuse querysets), context/complete
callbacks, dashboard, config, and per-phase surfaces (search, reports, insights).

---

## 4. Roadmap — phased, each phase is a shippable increment

> Each phase: **Objective → Build → Integration points → Acceptance criteria.**
> Do not start a phase before the previous one is merged and green.

### ✅ Phase 1 — Foundation + Chat Assistant (DONE)
- `ML_hostel/` service (provider abstraction + Ollama + agent tool loop + SSE).
- `apps/assistant/` BFF (context token, RBAC-scoped read-only tools —
  occupancy/dues/collections/find_students/counts, context + complete callbacks,
  AI dashboard, config). Models `Conversation`/`Message`/`AiUsage`.
- `features/ai/` (chat with live streaming, AI dashboard, nav). `ollama` +
  `ml_hostel` compose services + nginx `/ai` route.
- **Verified:** tenancy, RBAC on both auth paths, tool isolation, live LLM chat
  with tool-calling + streaming + persistence.

### ✅ Phase 2 — RAG / Knowledge Base (DONE)
- **Delivered:** `apps/aiknowledge` (`KnowledgeDocument` + `DocumentChunk`
  HostelScopedModel, CRUD viewset gated `ai.manage`/`ai.view` + `RequiresFeature
  ("ai_rag")`, upload/paste, `reingest`). Ingestion `@shared_task` (extract text via
  pypdf/txt/content → call the service to chunk+embed → persist chunks). System
  context token for background embed calls. `ML_hostel/rag/` (chunking + Ollama
  `nomic-embed-text` embeddings, provider-agnostic) + `/v1/ingest` `/v1/embed`.
  `search_knowledge` tool (tenant + `visibility`-filtered cosine retrieval);
  service embeds the query and injects the vector; assistant cites sources. FE
  Knowledge Base page (list/upload/paste/delete/reingest) + citation chips.
- **Vector store decision:** embeddings stored as an **in-DB JSON vector** with
  brute-force cosine in `apps/assistant/tools.py:_search_knowledge` — correct/fast
  at per-tenant KB scale, no infra swap (dev = host Postgres, prod = managed). The
  retriever is one function, so **pgvector is a drop-in** for scale later.
- **Verified:** 8 RAG tests (cosine ranking, tenant isolation, visibility, READY-
  only, RBAC, ingest-trigger) + service chunking tests; live ingest (text→READY
  with embeddings) + live RAG chat citing the source document.
- **Gates:** feature `ai_rag` (depends on `ai_chat`); `pypdf` added for PDF text.

### Phase 3 — Specialized Agents + Memory
- **Objective:** domain agents (finance, accounting, inventory, maintenance/
  complaints, HR/staff, admissions, reporting, executive) each with own tools,
  prompts, permissions, memory.
- **Build:** `ML_hostel/agents/<domain>.py` + per-agent tool sets (all reusing
  Django endpoints/querysets). Agent selector in the chat UI. Conversation memory:
  rolling summaries in `Message`/a `ConversationSummary` model; context compression.
- **Integration:** each agent's tools gated by the matching module perms
  (`finance.view`, `inventory.view`, …) already in the token. Gate behind
  `ai_agents`.
- **Acceptance:** the finance agent only exposes finance tools to finance-permitted
  users; memory persists across turns and respects tenancy.

### Phase 4 — AI Insights, Reports & Automation
- **Objective:** narrative reports (revenue, occupancy, dues, expenses, executive
  summary), scheduled digests (morning briefing, weekly/monthly), anomaly/risk
  alerts, and an automation engine (reminders, escalations, follow-ups).
- **Build:** `apps/assistant` report endpoints + a cross-domain analytics service
  (aggregate finance/occupancy/dues from domain models — NOT the PWA `analytics`
  app). Render PDF via **WeasyPrint** (already installed) and Excel via
  `exports.excel.wb_from_rows` (dormant helper). Delivery via
  `notifications.events.*`. Scheduling via new `CELERY_BEAT_SCHEDULE` entries +
  `@shared_task`. LLM summarization in the service.
- **Integration:** reuse `exports.csv_response`; reuse notifications; audit each
  generation. Gate behind `ai_reports`.
- **Acceptance:** a scheduled morning briefing is generated per tenant, delivered
  as a notification, downloadable as PDF/Excel, and never mixes tenants.

### Phase 5 — Prediction / Forecasting / Recommendations
- **Objective:** occupancy prediction, revenue forecasting (daily→yearly, with
  best/expected/worst scenarios + confidence), and smart recommendations (room/bed
  allocation, pricing, collection, purchasing, retention, risk).
- **Build:** `ML_hostel/prediction/` (start with statistical baselines —
  moving average / seasonal / linear trend — over domain queries; keep the model
  interface swappable for heavier models later). Expose via BFF endpoints +
  dashboard charts (recharts).
- **Integration:** query domain models directly for history; cache results in
  Redis; gate behind `ai_forecasting`.
- **Acceptance:** forecasts render with confidence bands; recommendations link to
  the action screen; all tenant-scoped.

### Phase 6 — Vision / OCR
- **Objective:** OCR for invoices/receipts/student IDs/citizenship/passport,
  asset QR/barcode, document parsing → prefill existing forms.
- **Build:** `ML_hostel/vision/` (provider-agnostic: Ollama vision models / hosted
  OCR). BFF endpoint accepts an upload (reuse `STORAGE_BACKEND`), returns structured
  fields that map onto existing serializers (admissions docs, inventory assets,
  finance expenses).
- **Acceptance:** extracted fields prefill the real create/edit forms; nothing is
  written without the normal RBAC-gated endpoint.

### Phase 7 — Voice
- **Objective:** speech-to-text (voice queries to the assistant) and optional
  text-to-speech, multi-language.
- **Build:** `ML_hostel/speech/` (provider-agnostic STT/TTS). Streaming audio into
  the existing chat flow; frontend mic capture + playback.
- **Acceptance:** a spoken question routes through the same agent/tool/RBAC path as
  text; no new data path.

### Phase 8 — Model Management
- **Objective:** provider/model registry, versioning, prompt library + versioning,
  A/B + canary routing, evaluation/benchmarking, cost/latency governance.
- **Build:** `apps/assistant` admin surface (models/prompts/providers config,
  `ai.manage`); service reads active config per tenant/flag. Frontend
  `features/ai` settings + prompt library pages.
- **Acceptance:** switching a tenant's model is config-only and audited; prompt
  versions are tracked and rollback-able.

### Phase 9 — Observability & Security Hardening
- **Objective:** Prometheus metrics (requests, tokens, latency, cost, success,
  hallucination/feedback), tracing, cost/latency alerts; prompt-injection &
  data-leakage defenses, PII masking, content filtering, kill switch.
- **Build:** extend the existing `django-prometheus` + `apps/security` +
  `platformops` kill-switch rather than new stacks. Feedback endpoints (thumbs
  up/down) on messages.
- **Acceptance:** the security ops dashboard shows AI metrics; the kill switch
  disables AI per tenant instantly; injection attempts are blocked and audited.

### Phase 10 — Tests, Docs, Rollout
- Full pytest + service tests + e2e (Playwright) for the AI surfaces; load test the
  SSE path; update `README`, `docs/`, and memory; staged rollout via feature flags
  and BETA→GA promotion in the subscription catalog.

---

## 5. Definition of Done (per phase)
1. Backend: new/changed code follows the reuse table §1; `python manage.py check`
   clean; migrations committed; pytest green incl. a cross-tenant isolation test.
2. Service: `py_compile` clean; provider-agnostic; service pytest green.
3. Frontend: `tsc --noEmit -p apps/admin` = 0 errors; nav + route policy wired.
4. Gating: RBAC perms + `RequiresFeature` + (metered) `enforce_limit` in place.
5. Audit: every mutation/AI action records an event.
6. Verified end-to-end against the running stack (drive the real flow, observe it).
7. `ML_hostel/README.md` + project memory updated. Nothing crosses tenants.

---

## 6. Operational notes (this environment)
- nginx config is bind-mounted → `docker compose exec nginx nginx -s reload` after
  edits to `deploy/dev/nginx/gateway.conf`.
- Do **not** run `uvicorn --reload` for `ml_hostel` under WSL — watchfiles OOMs and
  kills streams; restart with `docker compose restart ml_hostel` after edits.
- Ollama models: `docker compose exec ollama ollama pull <model>` (persisted in the
  `ollama_data` volume). CPU inference is slow here — use a small model in dev
  (`llama3.2:1b`/`qwen2.5:1.5b`) or a GPU/hosted provider in prod.
- `ML_SHARED_SECRET` must be identical for `web` and `ml_hostel`.
```
