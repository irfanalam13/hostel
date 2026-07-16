# Service Level Objectives & Error Budgets

**Phase 4, §4.** The measurable reliability targets the platform commits to, and
how we alert on them. SLIs/alerts are implemented as Prometheus rules
(`deploy/observability/prometheus/slo-rules.yml`, `ai-alerts.yml`).

## SLOs

| SLO | Target | Window | SLI (measurement) |
| --- | --- | --- | --- |
| **API availability** | 99.5% | 30 days | 1 − (5xx / total responses) |
| **API latency** | p95 < 1s | rolling | `django_http_requests_latency_seconds` p95 |
| **AI success rate** | ≥ 90% | rolling | 1 − (failed / total AI completions) |
| **AI latency** | p95 < 20s | rolling | `hostel_ai_latency_seconds` p95 |

Availability target 99.5% ⇒ **error budget = 0.5%** ≈ 3h 39m unavailability / 30
days.

## Burn-rate alerting

Instead of a flat "error rate > X" alert, we alert on how fast the error budget
is being consumed, over two windows (short confirms it's happening now; long
confirms it's sustained) — this pages on real incidents and stays quiet for
short blips.

| Alert | Condition | Budget impact | Action |
| --- | --- | --- | --- |
| `ErrorBudgetBurnFast` | burn > 14.4× on 5m **and** 1h | budget gone in ~2 days | **Page on-call** |
| `ErrorBudgetBurnSlow` | burn > 6× on 30m **and** 6h | sustained erosion | **Open a ticket** |

(burn rate = observed error ratio ÷ budget `0.005`.)

## AI guardrails

`AiErrorRateHigh` (>10% failures/10m), `AiLatencyP95High` (>20s/10m), and
`AiDailyCostGuardrail` (rolling 24h estimated spend > $25 — tune to budget).
Cost is estimated per request in `apps/assistant/metrics.py` and exposed as
`hostel_ai_cost_usd_total`.

## Operating the budget

- **Budget healthy** → ship features; use the progressive-delivery flow
  (`docs/PROGRESSIVE_DELIVERY.md`).
- **Budget burning (slow)** → prioritise reliability fixes over features.
- **Budget exhausted / fast burn** → freeze risky releases; the post-promotion
  metric gate (`deploy/scripts/metric_gate.py`) will auto-roll-back new deploys
  that breach the same thresholds.

Routing to notification channels is configured in
`deploy/observability/alertmanager/alertmanager.yml` (severity → receiver).
