# Operations Manual (Prompt 09)

Day-2 operations for the Hostel SaaS security & observability platform. Pairs
with `docs/OBSERVABILITY.md` (monitoring), `docs/EDGE_SECURITY.md` (Prompt 07),
`docs/AUTH_PROTECTION.md` (Prompt 08), `docs/PRODUCTION.md`, and the DR system
in `apps/backups`.

---

## 1. Daily operations

- **Dashboards** — Grafana → *Hostel — Security & Rate Limiting*. Watch the
  rate-limit allowed/limited ratio, auth-event rate, and WAF violations.
- **Threat report** — `manage.py security_report --period daily` (or
  `GET /api/platform/security/report/`). Archive weekly/monthly CSVs for
  compliance.
- **Alerts** — triage Alertmanager notifications by severity (below).
- **Posture check** — `GET /api/platform/security/summary/` shows live mode,
  fail strategy, WAF/bot modes, kill-switch state, and config generation.

---

## 2. Alert severities & first response

| Severity | Examples | First action |
|---|---|---|
| critical | Redis/Postgres/backend down | Check container health; `docker compose … ps`; restart the failed service; confirm auto-recovery |
| high | 5xx >5%, CPU/mem >90%, rate-limit/lockout surge | Open the security dashboard + top offenders; scale out or block sources |
| medium | p95 >1s, WAF surge | Investigate slow views / inspect matched WAF rules |
| low | bot activity | Consider Cloudflare Managed Challenge |

---

## 3. Incident response workflow

1. **Detect** — alert fires / dashboard anomaly / `summary/` threat level.
2. **Classify** — brute force, credential stuffing, DDoS/flood, WAF probes,
   bot campaign? Use `GET events/?event_type=…` and `GET offenders/`.
3. **Contain**:
   - Block an IP/range: `POST /api/platform/security/ip-rules/`
     `{ "cidr": "203.0.113.0/24", "action": "deny" }` (add `expires_at` for a
     temporary ban). Hot-reloads instantly.
   - Escalate enforcement: set `waf.mode` / `bots.mode` to `enforce`, or `mode`
     to `enforce`, via `POST settings/`.
   - Turn on CAPTCHA: `settings/` `{ "key": "auth.captcha.enabled", "value": true }`
     (needs `SECURITY_CAPTCHA_SECRET`).
   - Runaway protection causing an outage? Kill switch:
     `POST kill-switch/ { "target": "rate_limiter", "engage": true }`.
   - Total lockdown: `POST kill-switch/ { "target": "emergency", "engage": true }`
     (delegates to DR emergency mode).
4. **Investigate** — correlate metrics ↔ Loki logs ↔ traces on `request_id`;
   review the immutable `SecurityEvent` trail + `AuditEvent`.
5. **Recover** — restore with `engage:false` / set modes back / remove IP rules;
   confirm the dashboards return to baseline.
6. **Report** — generate a `security_report` for the window; attach to the
   incident record.
7. **Lessons learned** — tune thresholds (`threat.levels`), limits, or lockout
   tiers via `settings/` (no redeploy).

---

## 4. Automated blocking & recovery

- **Reputation** (Prompt 07) auto-penalises abusive IPs and temporarily blocks
  at threshold, decaying automatically (self-healing). Forgive early with
  `POST reputation/clear/ { "ip": "…" }`.
- **Progressive lockout** (Prompt 08) escalates auth blocks per tier and clears
  on success.
- **Temporary IP bans** — `IPRule` with `expires_at`; the daily
  `security-prune-events` task reaps expired rules.
- **Permanent bans** — `IPRule` without expiry; created only via the audited
  admin API (administrative approval trail).

---

## 5. Scaling & performance

- **Horizontal** — the app + workers are stateless; all rate-limit/reputation/
  lockout state is in shared Redis, so every decision stays correct across N
  containers. Scale `web`/`celery_worker` replicas behind the load balancer.
- **Redis HA** — for high load or fail-closed scopes, run Sentinel or Cluster
  (`SECURITY_REDIS_MODE`). Tune `maxmemory` + an LRU/LFU eviction policy;
  security keys all carry TTLs so they self-expire.
- **PostgreSQL** — `CONN_MAX_AGE` + health checks already on; add read replicas
  / pgbouncer for read-heavy analytics; the `SecurityEvent` table is indexed on
  `(event_type, created_at)` and `(ip, created_at)` and pruned by retention.
- **Load balancing** — round-robin or least-connections; sticky sessions are
  not required (JWT-cookie auth is stateless).
- **Multi-region** — the design is region-ready: per-region app + Redis, a
  shared/replicated Postgres, and Cloudflare geo-routing at the edge.

---

## 6. Rollback strategy

| Layer | Rollback |
|---|---|
| Config / rules | `settings/` + `ip-rules/` are DB rows — delete/revert; hot-reloads instantly. No deploy involved. |
| Feature flags | Every security subsystem has an `enabled` flag + the kill switch — disable without a deploy. |
| Deployment | `deploy/rollback.sh` re-pulls the previous image tag; health-gated. |
| Database | Migrations are reversible; DR restore engine (`apps/backups`) for data. |
| Emergency | Master switch `SECURITY_ENABLED=False` (env) disables the entire layer as a last resort. |

---

## 7. Troubleshooting

| Symptom | Likely cause | Check |
|---|---|---|
| Legit users 429'd | limits too tight / lockout tier low | `summary/`, `offenders/`; raise `rate_limits.*` / tiers via `settings/` |
| `/metrics` empty of `hostel_*` | `PROMETHEUS_ENABLED` off or no traffic yet | env + generate a request |
| Metrics but no logs in Loki | Promtail can't read Docker socket | promtail container logs + mounts |
| Config change not applied | generation not bumped / recheck window | `GET config/` shows `generation`; wait ≤ `SECURITY_CONFIG_RECHECK_SECONDS` |
| Rate limiting "off" | Redis down (fail-open) or kill switch engaged | Redis health; `summary/` → `posture.kill` |
| Everyone locked out of auth | bad lockout/captcha rule | `POST kill-switch/ {target:auth, engage:true}`, then fix the rule |

---

## 8. Compliance & audit

Immutable trails feed ISO 27001 / SOC 2 / GDPR evidence: `SecurityEvent`
(security decisions), `AuditEvent` (user/admin actions incl. every security-ops
mutation). Both are queryable and exportable (`security_report … --format csv`,
the audit API). Retention is configurable (`events.retention_days`) with a
daily prune. Logs are structured JSON with correlation ids throughout.
