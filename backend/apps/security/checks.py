"""Django system checks — misconfiguration fails fast at boot, not at 3am."""
import ipaddress
import os

from django.conf import settings
from django.core.checks import Error, Tags, Warning, register


@register(Tags.security)
def check_security_foundation(app_configs, **kwargs):
    issues = []

    strategy = os.environ.get("SECURITY_FAIL_STRATEGY", "").strip().lower()
    if strategy and strategy not in ("open", "closed"):
        issues.append(Error(
            f"SECURITY_FAIL_STRATEGY must be 'open' or 'closed' (got {strategy!r}).",
            id="security.E001",
        ))

    mode = os.environ.get("SECURITY_MODE", "").strip().lower()
    if mode and mode not in ("enforce", "monitor"):
        issues.append(Error(
            f"SECURITY_MODE must be 'enforce' or 'monitor' (got {mode!r}).",
            id="security.E002",
        ))

    for raw in (getattr(settings, "TRUSTED_PROXIES", None) or []):
        try:
            ipaddress.ip_network(str(raw).strip(), strict=False)
        except ValueError:
            issues.append(Error(
                f"TRUSTED_PROXIES contains an invalid CIDR: {raw!r}.",
                id="security.E003",
            ))

    config_file = getattr(settings, "SECURITY_CONFIG_FILE", "")
    if config_file:
        try:
            import yaml  # noqa: F401
        except ImportError:
            issues.append(Error(
                "SECURITY_CONFIG_FILE is set but PyYAML is not installed "
                "(pip install PyYAML).",
                id="security.E004",
            ))
        if not os.path.exists(config_file):
            issues.append(Warning(
                f"SECURITY_CONFIG_FILE {config_file!r} does not exist — the "
                "YAML layer will be skipped.",
                id="security.W001",
            ))

    if not settings.DEBUG and mode == "monitor":
        issues.append(Warning(
            "SECURITY_MODE=monitor in production: violations are logged but "
            "nothing is blocked. Intended only for a soak period.",
            id="security.W002",
        ))

    if not settings.DEBUG and strategy == "closed":
        issues.append(Warning(
            "SECURITY_FAIL_STRATEGY=closed: a Redis outage will reject "
            "traffic on rate-limited scopes (503). Ensure Redis is HA "
            "(Sentinel/Cluster) before choosing fail-closed.",
            id="security.W003",
        ))

    return issues
