"""Layered security configuration with runtime hot reload.

Resolution order (later layers win):

    1. ``defaults.DEFAULTS``
    2. ``defaults.ENVIRONMENT_DEFAULTS[SECURITY_ENVIRONMENT]``
    3. YAML file (``SECURITY_CONFIG_FILE``) — infra-managed policy
    4. Environment variables (``SECURITY_*`` — see ``_ENV_OVERRIDES``)
    5. Database ``SecuritySetting`` rows (dotted key -> JSON value) — runtime,
       hot-reloaded without redeploy via a Redis generation counter

The resolved snapshot (including compiled IP networks and DB ``IPRule`` rows)
is cached in-process and rebuilt when the generation counter changes (bumped
by ``signals.py`` on any SecuritySetting/IPRule change) or every
``SECURITY_CONFIG_RECHECK_SECONDS`` — so a change on ANY app container
propagates to ALL containers within seconds, no restart.

A cache/DB outage never breaks resolution: each layer degrades independently
to the previous one.
"""
import copy
import ipaddress
import json
import logging
import os
import threading
import time

from django.conf import settings
from django.core.cache import cache

from .defaults import DEFAULTS, ENVIRONMENT_DEFAULTS

logger = logging.getLogger("apps.security")

_GEN_KEY = "sec:conf:gen"

_lock = threading.Lock()
_snapshot = None            # SecurityConfig
_snapshot_gen = None        # generation it was built at
_last_check = 0.0           # monotonic time of last generation check


# --------------------------------------------------------------------------- #
# Merging helpers
# --------------------------------------------------------------------------- #
def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge ``override`` into a copy of ``base``. Lists and
    scalars are replaced wholesale (policy lists are intentional overrides,
    not unions)."""
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def _set_path(data: dict, dotted: str, value) -> None:
    """Set ``data['a']['b']['c'] = value`` for dotted key ``a.b.c``."""
    parts = [p for p in dotted.split(".") if p]
    if not parts:
        return
    node = data
    for part in parts[:-1]:
        nxt = node.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            node[part] = nxt
        node = nxt
    node[parts[-1]] = value


def _coerce(raw: str):
    """Best-effort typing for env-var overrides: JSON first (numbers, bools,
    lists, objects), then comma-list, then plain string."""
    raw = raw.strip()
    if not raw:
        return raw
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        pass
    lowered = raw.lower()
    if lowered in ("true", "yes", "on"):
        return True
    if lowered in ("false", "no", "off"):
        return False
    if "," in raw:
        return [item.strip() for item in raw.split(",") if item.strip()]
    return raw


# Environment-variable overrides: ENV NAME -> dotted config path. Values are
# coerced with _coerce (JSON / bool / comma-list / string). Documented in
# .env.example. Anything not listed here is still reachable via
# SECURITY_CONFIG_FILE (YAML) or SecuritySetting (DB).
_ENV_OVERRIDES = {
    "SECURITY_MODE": "mode",
    "SECURITY_FAIL_STRATEGY": "fail_strategy",
    "SECURITY_BACKEND": "backend",
    "SECURITY_TRUSTED_PROXIES": "trusted_proxies",
    "SECURITY_EXEMPT_PATHS": "exempt_paths",
    "SECURITY_CLOUDFLARE_ENABLED": "cloudflare.enabled",
    "SECURITY_CLOUDFLARE_IP_RANGES": "cloudflare.ip_ranges",
    "SECURITY_IP_RULES_ENABLED": "ip_rules.enabled",
    "SECURITY_REPUTATION_ENABLED": "reputation.enabled",
    "SECURITY_REPUTATION_BLOCK_THRESHOLD": "reputation.block_threshold",
    "SECURITY_REPUTATION_BLOCK_SECONDS": "reputation.block_seconds",
    "SECURITY_BOTS_ENABLED": "bots.enabled",
    "SECURITY_BOTS_MODE": "bots.mode",
    "SECURITY_WAF_ENABLED": "waf.enabled",
    "SECURITY_WAF_MODE": "waf.mode",
    "SECURITY_RATE_IP_LIMIT": "rate_limits.ip_global.limit",
    "SECURITY_RATE_IP_WINDOW": "rate_limits.ip_global.window_seconds",
    "SECURITY_RATE_IP_BURST_CAPACITY": "rate_limits.ip_burst.capacity",
    "SECURITY_RATE_IP_BURST_REFILL": "rate_limits.ip_burst.refill_rate",
    "SECURITY_RATE_TENANT_LIMIT": "rate_limits.tenant_global.limit",
    "SECURITY_RATE_TENANT_WINDOW": "rate_limits.tenant_global.window_seconds",
    "SECURITY_EVENTS_PERSIST": "events.persist",
    "SECURITY_EVENTS_RETENTION_DAYS": "events.retention_days",
    # Auth protection (Prompt 08)
    "SECURITY_AUTH_ENABLED": "auth.enabled",
    "SECURITY_LOCKOUT_ENABLED": "auth.progressive_lockout.enabled",
    "SECURITY_LOCKOUT_TIERS": "auth.progressive_lockout.tiers",
    "SECURITY_LOCKOUT_WINDOW": "auth.progressive_lockout.failure_window_seconds",
    "SECURITY_CAPTCHA_ENABLED": "auth.captcha.enabled",
    "SECURITY_CAPTCHA_PROVIDER": "auth.captcha.provider",
    "SECURITY_CAPTCHA_TRIGGER_AFTER": "auth.captcha.trigger_after_failures",
    "SECURITY_ROLE_LIMITS_ENABLED": "role_limits.enabled",
}


# --------------------------------------------------------------------------- #
# Layer loaders
# --------------------------------------------------------------------------- #
def _environment() -> str:
    envname = getattr(settings, "SECURITY_ENVIRONMENT", "") or (
        "development" if settings.DEBUG else "production"
    )
    return envname if envname in ENVIRONMENT_DEFAULTS else "production"


def _load_yaml_layer() -> dict:
    path = getattr(settings, "SECURITY_CONFIG_FILE", "") or os.environ.get(
        "SECURITY_CONFIG_FILE", ""
    )
    if not path:
        return {}
    try:
        import yaml  # PyYAML — required only when a config file is used
    except ImportError:
        logger.error("SECURITY_CONFIG_FILE is set but PyYAML is not installed.")
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        if not isinstance(data, dict):
            logger.error("security config file %s must contain a mapping", path)
            return {}
        return data
    except OSError as exc:
        logger.error("security config file %s unreadable: %s", path, exc)
        return {}


def _load_env_layer() -> dict:
    layer: dict = {}
    for env_name, dotted in _ENV_OVERRIDES.items():
        raw = os.environ.get(env_name)
        if raw is not None and raw != "":
            _set_path(layer, dotted, _coerce(raw))
    # Legacy/global alias kept for consistency with the rest of settings.py.
    trusted = getattr(settings, "TRUSTED_PROXIES", None)
    if trusted:
        _set_path(layer, "trusted_proxies", list(trusted))
    return layer


def _load_db_layer() -> dict:
    """Runtime overrides from SecuritySetting rows. Degrades to {} when the
    table doesn't exist yet (first migrate) or the DB is unavailable."""
    layer: dict = {}
    try:
        from .models import SecuritySetting

        for row in SecuritySetting.objects.filter(active=True).values_list("key", "value"):
            _set_path(layer, row[0], row[1])
    except Exception:  # pragma: no cover — pre-migrate boot / DB outage
        logger.debug("security DB config layer unavailable", exc_info=True)
    return layer


def _load_ip_rules():
    """Active IPRule rows compiled to (network, action, tenant_id, rule_id).
    Expired temporary rules are filtered out at load time."""
    rules = []
    try:
        from django.utils import timezone

        from .models import IPRule

        now = timezone.now()
        qs = IPRule.objects.filter(active=True).values_list(
            "cidr", "action", "tenant_id", "expires_at", "id"
        )
        for cidr, action, tenant_id, expires_at, rule_id in qs:
            if expires_at and expires_at <= now:
                continue
            try:
                network = ipaddress.ip_network(cidr, strict=False)
            except ValueError:
                logger.warning("IPRule %s has invalid CIDR %r — skipped", rule_id, cidr)
                continue
            rules.append((network, action, tenant_id, rule_id))
    except Exception:  # pragma: no cover — pre-migrate boot / DB outage
        logger.debug("security IP rules unavailable", exc_info=True)
    return rules


def _compile_networks(cidrs) -> list:
    networks = []
    for cidr in cidrs or []:
        try:
            networks.append(ipaddress.ip_network(str(cidr).strip(), strict=False))
        except ValueError:
            logger.warning("invalid CIDR %r in security config — skipped", cidr)
    return networks


# --------------------------------------------------------------------------- #
# Snapshot
# --------------------------------------------------------------------------- #
class SecurityConfig:
    """Immutable resolved snapshot with pre-compiled lookups."""

    def __init__(self, data: dict, ip_rules, generation: int):
        self.data = data
        self.generation = generation
        self.trusted_proxy_networks = _compile_networks(data.get("trusted_proxies"))
        self.cloudflare_networks = _compile_networks(
            (data.get("cloudflare") or {}).get("ip_ranges")
        )
        self.exempt_paths = tuple(data.get("exempt_paths") or [])
        self.ip_rules = ip_rules  # [(network, action, tenant_id, rule_id)]

    # -- generic access ---------------------------------------------------- #
    def get(self, dotted: str, default=None):
        node = self.data
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    @property
    def enabled(self) -> bool:
        if not getattr(settings, "SECURITY_ENABLED", True):
            return False
        return bool(self.data.get("enabled", True))

    @property
    def monitor_only(self) -> bool:
        return str(self.data.get("mode", "enforce")).lower() == "monitor"

    @property
    def fail_open(self) -> bool:
        return str(self.data.get("fail_strategy", "open")).lower() != "closed"

    def section_enforces(self, section: str) -> bool:
        """True when violations in ``section`` (waf/bots) should block. The
        global monitor mode always wins (never block in monitor)."""
        if self.monitor_only:
            return False
        return str(self.get(f"{section}.mode", "enforce")).lower() == "enforce"

    # -- lookups ------------------------------------------------------------ #
    def is_trusted_proxy(self, ip) -> bool:
        return any(ip in net for net in self.trusted_proxy_networks)

    def is_cloudflare(self, ip) -> bool:
        return any(ip in net for net in self.cloudflare_networks)

    def is_exempt_path(self, path: str) -> bool:
        return path.startswith(self.exempt_paths) if self.exempt_paths else False

    def match_ip_rule(self, ip, tenant_id=None):
        """First matching rule for this address. Tenant-scoped rules apply
        only to their workspace; global rules (tenant_id NULL) to everyone.
        Precedence: trust > allow > deny (a trusted/allowed IP can never be
        locked out by a broader deny)."""
        if not self.get("ip_rules.enabled", True):
            return None
        matches = [
            (action, rule_id)
            for network, action, rule_tenant, rule_id in self.ip_rules
            if (rule_tenant is None or rule_tenant == tenant_id) and ip in network
        ]
        if not matches:
            return None
        for wanted in ("trust", "allow", "deny"):
            for action, rule_id in matches:
                if action == wanted:
                    return action, rule_id
        return matches[0]

    def plan_multiplier(self, plan_slug: str) -> float:
        table = self.data.get("plan_multipliers") or {}
        try:
            return float(table.get((plan_slug or "").lower(), table.get("default", 1.0)))
        except (TypeError, ValueError):
            return 1.0


# --------------------------------------------------------------------------- #
# Generation counter (hot reload across all containers)
# --------------------------------------------------------------------------- #
def generation() -> int:
    try:
        gen = cache.get(_GEN_KEY)
        if gen is None:
            cache.add(_GEN_KEY, 1, timeout=None)
            gen = cache.get(_GEN_KEY) or 1
        return int(gen)
    except Exception:
        return 1


def bump() -> None:
    """Invalidate every container's cached snapshot (called from signals)."""
    global _last_check
    try:
        try:
            cache.incr(_GEN_KEY)
        except ValueError:
            cache.set(_GEN_KEY, 1, timeout=None)
    except Exception:
        logger.warning("security config generation bump failed", exc_info=True)
    _last_check = 0.0  # force this process to re-check immediately


def _build(gen: int) -> SecurityConfig:
    data = _deep_merge(DEFAULTS, ENVIRONMENT_DEFAULTS.get(_environment(), {}))
    data = _deep_merge(data, _load_yaml_layer())
    data = _deep_merge(data, _load_env_layer())
    data = _deep_merge(data, _load_db_layer())
    return SecurityConfig(data, _load_ip_rules(), gen)


def get_config() -> SecurityConfig:
    """The current resolved snapshot. Cheap: a monotonic-clock check per call,
    one Redis GET at most every SECURITY_CONFIG_RECHECK_SECONDS, and a full
    rebuild only when the generation actually changed."""
    global _snapshot, _snapshot_gen, _last_check

    recheck = float(getattr(settings, "SECURITY_CONFIG_RECHECK_SECONDS", 5))
    now = time.monotonic()

    if _snapshot is not None and (now - _last_check) < recheck:
        return _snapshot

    with _lock:
        now = time.monotonic()
        if _snapshot is not None and (now - _last_check) < recheck:
            return _snapshot
        gen = generation()
        if _snapshot is None or gen != _snapshot_gen:
            _snapshot = _build(gen)
            _snapshot_gen = gen
            logger.info("security config loaded (generation=%s)", gen)
        _last_check = now
        return _snapshot


def reset_for_tests() -> None:
    """Drop the process-local snapshot (test isolation helper)."""
    global _snapshot, _snapshot_gen, _last_check
    with _lock:
        _snapshot = None
        _snapshot_gen = None
        _last_check = 0.0
