#!/usr/bin/env python3
"""Post-promotion metric gate with automatic rollback (Phase 3, §3 CD).

After a production promotion (Render/Vercel — see docs/CD_STRATEGY.md), this
watches the two SLOs that already back our Prometheus alerts:

  * 5xx error rate  = sum(rate(django_http_responses_total_by_status_total{status=~"5.."}[5m]))
                      / clamp_min(sum(rate(django_http_responses_total_by_status_total[5m])), 1)
  * p95 latency     = histogram_quantile(0.95,
                        sum(rate(django_http_requests_latency_seconds_by_view_method_bucket[5m])) by (le))

It polls for a bake window; if either SLO breaches for N consecutive checks it
runs the supplied rollback command and exits non-zero (failing the deploy job).
Stdlib only, so it runs anywhere with no install. The evaluation core is a pure
function (`classify`) so it is unit-tested without a live Prometheus.

Example (CI):
  python deploy/scripts/metric_gate.py \
    --prom-url "$PROM_URL" --bake-seconds 600 --interval 30 \
    --max-error-rate 0.05 --max-p95 1.0 --breach-threshold 3 \
    --rollback-cmd 'bash deploy/scripts/rollback_render.sh'
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.parse
import urllib.request

# SLO PromQL — kept identical to deploy/observability/prometheus/alerts.yml so the
# gate and the alerts never disagree about what "unhealthy" means.
ERROR_RATE_QUERY = (
    'sum(rate(django_http_responses_total_by_status_total{status=~"5.."}[5m]))'
    " / clamp_min(sum(rate(django_http_responses_total_by_status_total[5m])), 1)"
)
P95_LATENCY_QUERY = (
    "histogram_quantile(0.95, sum(rate("
    "django_http_requests_latency_seconds_by_view_method_bucket[5m])) by (le))"
)


class Thresholds:
    def __init__(self, max_error_rate: float, max_p95: float):
        self.max_error_rate = max_error_rate
        self.max_p95 = max_p95


def classify(error_rate: float | None, p95: float | None, t: Thresholds) -> list[str]:
    """Pure: return the list of breached SLOs (empty = healthy).

    A `None` sample (metric absent / not yet scraped) is treated as NOT a breach
    so a cold target during the first scrape doesn't trigger a false rollback.
    """
    breaches = []
    if error_rate is not None and error_rate > t.max_error_rate:
        breaches.append(f"error_rate={error_rate:.4f} > {t.max_error_rate}")
    if p95 is not None and p95 > t.max_p95:
        breaches.append(f"p95={p95:.3f}s > {t.max_p95}s")
    return breaches


def query_prometheus(base_url: str, expr: str, timeout: float = 10.0) -> float | None:
    """Run an instant query; return the scalar value or None if no data."""
    url = base_url.rstrip("/") + "/api/v1/query?" + urllib.parse.urlencode({"query": expr})
    with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310 (trusted internal URL)
        payload = json.loads(resp.read().decode("utf-8"))
    if payload.get("status") != "success":
        raise RuntimeError(f"Prometheus query failed: {payload}")
    result = payload["data"]["result"]
    if not result:
        return None
    value = float(result[0]["value"][1])
    # Prometheus returns NaN as the string 'NaN'; treat as no-data.
    return None if value != value else value


def run_rollback(cmd: str, dry_run: bool) -> None:
    if dry_run:
        print(f"[dry-run] would run rollback: {cmd}")
        return
    print(f"::warning::Triggering rollback: {cmd}")
    subprocess.run(cmd, shell=True, check=True)  # noqa: S602 (operator-supplied)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Prometheus SLO gate with auto-rollback.")
    p.add_argument("--prom-url", required=True, help="Base URL of Prometheus (query API).")
    p.add_argument("--bake-seconds", type=int, default=600, help="Total watch window.")
    p.add_argument("--interval", type=int, default=30, help="Seconds between checks.")
    p.add_argument("--max-error-rate", type=float, default=0.05)
    p.add_argument("--max-p95", type=float, default=1.0)
    p.add_argument("--breach-threshold", type=int, default=3,
                   help="Consecutive breached checks that trigger rollback.")
    p.add_argument("--rollback-cmd", default="",
                   help="Shell command to roll back (empty = report only, no rollback).")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    t = Thresholds(args.max_error_rate, args.max_p95)
    deadline = time.monotonic() + args.bake_seconds
    consecutive = 0
    check = 0

    print(f"Metric gate: baking {args.bake_seconds}s, checking every {args.interval}s "
          f"(error>{t.max_error_rate}, p95>{t.max_p95}s, {args.breach_threshold} consecutive breaches → rollback).")

    while time.monotonic() < deadline:
        check += 1
        try:
            err = query_prometheus(args.prom_url, ERROR_RATE_QUERY)
            p95 = query_prometheus(args.prom_url, P95_LATENCY_QUERY)
        except Exception as exc:  # network/Prom hiccup: log, don't count as breach
            print(f"  check #{check}: query error ({exc}); skipping this tick")
            time.sleep(args.interval)
            continue

        breaches = classify(err, p95, t)
        if breaches:
            consecutive += 1
            print(f"  check #{check}: BREACH ({consecutive}/{args.breach_threshold}) — {'; '.join(breaches)}")
            if consecutive >= args.breach_threshold:
                print(f"::error::SLO breached {consecutive} consecutive checks — rolling back.")
                if args.rollback_cmd:
                    run_rollback(args.rollback_cmd, args.dry_run)
                return 1
        else:
            if consecutive:
                print(f"  check #{check}: recovered (was {consecutive} breaches); resetting.")
            consecutive = 0
            print(f"  check #{check}: healthy (error={err}, p95={p95}).")

        time.sleep(args.interval)

    print("✓ Bake window elapsed with SLOs healthy — promotion confirmed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
