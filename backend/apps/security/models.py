"""Persistence for the security foundation.

* ``SecuritySetting`` — runtime config overrides (dotted key -> JSON value),
  the top layer of the config chain; editing a row hot-reloads every
  container within seconds (signals bump the generation counter).
* ``IPRule``          — operator-managed allow / deny / trust CIDRs, global
  or scoped to one workspace; optional expiry makes temporary bans reap
  themselves.
* ``SecurityEvent``   — append-only audit trail of every security decision
  (WAF block, rate-limit trigger, bot block, reputation change, ...).
  Rows are never updated (admin is read-only) and are pruned by retention.
"""
from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class SecuritySetting(TimeStampedModel):
    """One runtime config override: ``key`` is a dotted path into the security
    config (e.g. ``waf.mode``), ``value`` is the JSON value to place there."""

    key = models.CharField(max_length=190, unique=True)
    value = models.JSONField()
    active = models.BooleanField(default=True)
    note = models.CharField(max_length=255, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        verbose_name = "security setting"

    def __str__(self):
        return f"{self.key} = {self.value!r}"


class IPRuleAction(models.TextChoices):
    TRUST = "trust", "Trust (skip all security checks)"
    ALLOW = "allow", "Allow (bypass rate limits / reputation)"
    DENY = "deny", "Deny (block outright)"


class IPRule(TimeStampedModel):
    cidr = models.CharField(
        max_length=64,
        help_text="Single IP or CIDR, IPv4/IPv6 (e.g. 203.0.113.7 or 10.0.0.0/8).",
    )
    action = models.CharField(max_length=8, choices=IPRuleAction.choices)
    # NULL = platform-wide; set = applies only to that workspace's traffic.
    tenant = models.ForeignKey(
        "tenants.Hostel", null=True, blank=True, on_delete=models.CASCADE,
        related_name="ip_rules",
    )
    active = models.BooleanField(default=True)
    # NULL = permanent. Expired rules are ignored at load time and pruned.
    expires_at = models.DateTimeField(null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        verbose_name = "IP rule"
        indexes = [models.Index(fields=["active", "action"])]

    def __str__(self):
        scope = self.tenant.slug if self.tenant_id and self.tenant else "global"
        return f"{self.action} {self.cidr} ({scope})"


class SecurityEventType(models.TextChoices):
    RATE_LIMITED = "rate_limited", "Rate limit triggered"
    WAF_VIOLATION = "waf_violation", "WAF rule matched"
    BOT_DETECTED = "bot_detected", "Bot detected"
    IP_DENIED = "ip_denied", "IP rule deny"
    REPUTATION_BLOCK = "reputation_block", "Reputation block"
    REPUTATION_CHANGE = "reputation_change", "Reputation change"
    PROXY_SUSPECT = "proxy_suspect", "Forwarded-chain anomaly"
    FAIL_CLOSED = "fail_closed", "Fail-closed rejection"
    CONFIG_CHANGE = "config_change", "Security config change"
    # Authentication protection (Prompt 08)
    AUTH_FAILURE = "auth_failure", "Authentication failure"
    AUTH_LOCKOUT = "auth_lockout", "Progressive lockout triggered"
    CAPTCHA_REQUIRED = "captcha_required", "CAPTCHA challenge required"
    CAPTCHA_FAILED = "captcha_failed", "CAPTCHA verification failed"
    API_ROLE_LIMITED = "api_role_limited", "Per-role API limit"
    REPLAY_BLOCKED = "replay_blocked", "Replay attempt blocked"


class SecurityEvent(models.Model):
    """Append-only. No updated_at, no updates — an immutable audit record."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    event_type = models.CharField(max_length=32, choices=SecurityEventType.choices)
    action = models.CharField(max_length=16, blank=True)     # logged | blocked | allowed
    ip = models.CharField(max_length=64, blank=True)
    method = models.CharField(max_length=10, blank=True)
    path = models.CharField(max_length=255, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    request_id = models.CharField(max_length=64, blank=True)
    country = models.CharField(max_length=8, blank=True)     # from CF-IPCountry
    asn = models.CharField(max_length=16, blank=True)
    threat_score = models.IntegerField(default=0)
    tenant = models.ForeignKey(
        "tenants.Hostel", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="security_events",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="security_events",
    )
    detail = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "security event"
        indexes = [
            models.Index(fields=["event_type", "created_at"]),
            models.Index(fields=["ip", "created_at"]),
        ]

    def __str__(self):
        return f"{self.event_type} {self.ip} {self.path}"
