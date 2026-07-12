"""Enterprise edge-security & rate-limiting foundation.

Layered defence for the whole platform:

    Cloudflare (optional) -> Nginx -> Redis distributed limiter ->
    EdgeGuardMiddleware (IP rules, reputation, bots, WAF-lite, IP limits) ->
    TenantRateLimitMiddleware (per-workspace, plan-aware) ->
    DRF throttles (endpoint-specific, next prompt) -> business logic

Everything is configuration-driven (defaults -> YAML -> env -> DB overrides)
with Redis-backed hot reload, per-tenant isolation, monitor/enforce modes and
a configurable fail-open / fail-closed strategy. See docs/EDGE_SECURITY.md.
"""
