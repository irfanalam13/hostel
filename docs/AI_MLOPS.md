# AI / MLOps

**Phase 6.** Holds the AI layer (`ML_hostel` service + `apps/assistant` gateway)
to the same engineering bar as the rest of the platform: versioned, evaluated,
guard-railed, observable, and safely promotable. Ties together work from
Phases 3–6.

## Lifecycle at a glance

```
 prompt/model change
   │
   ├─ EVAL GATE (CI) ......... deterministic prompt-contract + golden set + registry
   │                           ML_hostel/tests/test_eval_prompts.py → test-ml job
   ├─ VERSIONED ............. PROMPT_VERSION + approved-model registry
   ├─ SHIP DARK ............. behind a feature flag (release_flag), rollout 0%
   ├─ RAMP + OBSERVE ........ metrics/cost (hostel_ai_*), alerts, SLOs
   ├─ GUARDRAILS ............ input cap + daily cost budget at the gateway
   └─ FEEDBACK → DRIFT ...... 👎 answers → ai_eval_export → new eval cases
```

## 1. Versioning (attribution + safe promotion)

- **`PROMPT_VERSION`** (`ML_hostel/app/agents/prompts.py`) — bump on any prompt
  change; recorded on every `AiUsage.meta.prompt_version`, so quality/cost is
  attributable to a prompt version.
- **Approved-model registry** (`ML_hostel/app/llm/registry.py`) — only vetted
  model IDs are allowed; a new model must be added via PR (which runs the eval
  gate) before promotion. `assert_model_approved` fails closed.

## 2. Eval gate (CI)

`ML_hostel/tests/test_eval_prompts.py` (runs in the `test-ml` CI job) asserts the
system prompt keeps its safety guardrails (tool-grounding, no-guessing,
cite-sources, strict tenant scoping), passes a golden context set, keeps
`PROMPT_VERSION` set, and that the registry rejects unapproved models. A
live-model eval is opt-in (`ML_EVAL_LIVE=1`). **A prompt regression can't merge.**

## 3. Dark rollout (promotion)

Gate a new model/prompt behind a flag and ramp it — never a big-bang swap:

```bash
python manage.py release_flag ai_model_gemini_2 --activate --rollout 10
python manage.py release_flag ai_model_gemini_2 --rollout 50
python manage.py release_flag ai_model_gemini_2 --kill      # instant rollback
```

See `docs/PROGRESSIVE_DELIVERY.md`. The metric gate
(`deploy/scripts/metric_gate.py`) also auto-rolls-back a deploy that breaches SLOs.

## 4. Guardrails (gateway choke point)

`apps/assistant/guardrails.py`, enforced in `ChatSessionView` before a token is
spent:
- **Input cap** — `AI_MAX_INPUT_CHARS` (default 8000).
- **Daily cost budget** — `AI_DAILY_COST_BUDGET_USD` (default 0 = off) using the
  estimated `cost_usd` recorded per request.
- RBAC/tenant scoping is already enforced by the signed context token + the tool
  layer (`apps/assistant/tools.py`).

## 5. Observability & cost (Phase 4)

`apps/assistant/metrics.py` emits `hostel_ai_requests_total`, `..._tokens_total`,
`..._cost_usd_total`, `..._latency_seconds`. Alerts in
`deploy/observability/prometheus/ai-alerts.yml` (error rate, p95 latency, daily
cost guardrail). Cost is estimated per request from a price table.

## 6. Drift / feedback loop

- Users rate answers 👍/👎 → `POST /api/ai/conversations/<id>/feedback/`
  (stored on `AiUsage.meta.feedback`, no schema change).
- **`python manage.py ai_eval_export --days 30 --out eval-candidates.json`**
  turns thumbs-down / errored answers into eval candidates. Review them and fold
  genuine misses into the golden set — so the eval gate grows to cover real
  failures, not just synthetic prompts. Run it on a schedule and triage.

## Configuration summary

| Setting / env | Default | Purpose |
| --- | --- | --- |
| `AI_MAX_INPUT_CHARS` | 8000 | Reject oversized prompts |
| `AI_DAILY_COST_BUDGET_USD` | 0 (off) | Per-tenant daily spend ceiling |
| `PROMPT_VERSION` | date-based | Prompt attribution |
| `ML_MODEL` / `ML_PROVIDER` | per env | Must be in the approved registry |
| `ML_EVAL_LIVE` | unset | Opt-in live-model eval |
