# Progressive Delivery

**Phase 3, §3.** How we ship risky changes safely on the Render + Vercel PaaS:
**deploy dark → ramp exposure → watch SLOs → auto-rollback on breach**, with an
instant flag kill as the manual escape hatch. Builds on `docs/CD_STRATEGY.md`
(the manual production promotion gate).

Two independent, complementary controls:

| Control | Mechanism | Rolls back by |
| --- | --- | --- |
| **Release exposure** | Feature flags (`apps.platformops`) | Flipping a flag — no deploy |
| **Release health** | Prometheus SLO gate (`deploy/scripts/metric_gate.py`) | Rolling the Render deploy back |

## 1. Feature-flag (dark) releases

Wrap the new path in the existing flag engine:

```python
from apps.platformops.flags import is_enabled

if is_enabled("checkout_v2", hostel=request.hostel, user=request.user):
    ... # new path
else:
    ... # old path
```

Drive the rollout with the `release_flag` management command (thin wrapper over
the flag model; changes are live immediately via cache invalidation):

```bash
# 1. Ship dark — code is deployed, feature is OFF for everyone
python manage.py release_flag checkout_v2 --name "Checkout v2"

# 2. Canary to staff only, then ramp by deterministic % (stable per tenant)
python manage.py release_flag checkout_v2 --activate --roles OWNER,ADMIN
python manage.py release_flag checkout_v2 --rollout 10
python manage.py release_flag checkout_v2 --rollout 50
python manage.py release_flag checkout_v2 --rollout 100

# 3. INSTANT ROLLBACK — kill beats all rules, no redeploy
python manage.py release_flag checkout_v2 --kill
```

The engine's evaluation order (see `flags.py`) makes `--kill` an absolute
off-switch, and `--rollout` a deterministic per-tenant bucket so a tenant's
experience is stable as the percentage climbs.

## 2. Metric-based auto-rollback

After promoting to production (Render "Manual Deploy" / Vercel "Promote"), run
the **Post-promotion metric gate** workflow (`.github/workflows/deploy-verify.yml`)
or the script directly. It watches the same two SLOs that back our alerts
(`alerts.yml`): **5xx error rate > 5%** and **p95 latency > 1s**. If either
breaches for 3 consecutive checks over the bake window, it runs the rollback
command and fails the job.

```bash
python deploy/scripts/metric_gate.py \
  --prom-url "$PROM_URL" --bake-seconds 600 --interval 30 \
  --max-error-rate 0.05 --max-p95 1.0 --breach-threshold 3 \
  --rollback-cmd 'bash deploy/scripts/rollback_render.sh'   # RENDER_API_KEY + RENDER_SERVICE_ID
```

Required secrets (scoped to the `production` GitHub Environment): `PROM_URL`,
`RENDER_API_KEY`, `RENDER_BACKEND_SERVICE_ID`. Use `--dry-run` to rehearse
without rolling back. The evaluation core is unit-tested
(`deploy/scripts/test_metric_gate.py`).

> Vercel rollback is an *Instant Rollback* on the previous production deployment;
> swap the `--rollback-cmd` for a Vercel-CLI call if the frontend is the suspect.

## 3. AI model / prompt promotion (§3 AI overlay)

New LLM models or system-prompt changes are **higher-risk than code** (quality can
regress silently), so they get their own gate:

1. **Eval gate (CI):** `ML_hostel/tests/test_eval_prompts.py` asserts the system
   prompt keeps its safety-critical directives (tool-grounding, no-guessing,
   cite-sources, strict tenant scoping) and passes a golden set. It runs in CI
   (`test-ml` job) and blocks the merge on regression. A live-LLM eval is opt-in
   (`ML_EVAL_LIVE=1`) so CI stays fast and non-flaky.
2. **Dark model rollout:** gate a new model/prompt behind a flag
   (`is_enabled("ai_model_gemini_2", hostel=...)`) and ramp with `release_flag`
   exactly like any other feature — so a bad model is a flag flip away from off,
   never a redeploy.

## Checklist for a risky release

- [ ] Code merged behind `is_enabled("<flag>")`, shipped dark (`--rollout 0`).
- [ ] Promote to production (manual gate, `CD_STRATEGY.md`).
- [ ] Run `deploy-verify.yml` (or the script) for the bake window.
- [ ] Ramp `--rollout` 10 → 50 → 100, watching Grafana between steps.
- [ ] If anything smells wrong: `release_flag <flag> --kill` (feature) and/or let
      the metric gate roll the deploy back (infra).
