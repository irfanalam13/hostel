"""CAPTCHA escalation — trigger decision + server-side verification.

Providers: Cloudflare Turnstile, Google reCAPTCHA v2/v3, hCaptcha. All three
expose the same verify contract (POST secret+response, JSON `success`), so one
verifier covers them via a provider→endpoint map.

Policy (`auth.captcha`): a challenge is required only when the auth layer has
reason to — after `trigger_after_failures` failed attempts, or when the source
IP reputation is at/above `trigger_on_reputation`. Never required otherwise
(a first, clean login is never challenged).

Safety: CAPTCHA is a hard no-op until `SECURITY_CAPTCHA_SECRET` is set, no
matter the config flags — so enabling the flag without a secret can't lock
everyone out. Verification network errors honour `fail_open` (default allow,
availability first). The secret is read from settings/env only, never from the
DB/YAML config layers.
"""
import logging

from django.conf import settings

from . import reputation
from .conf import get_config

logger = logging.getLogger("apps.security")

# provider -> (verify endpoint, response field name the client submits)
_PROVIDERS = {
    "turnstile": ("https://challenges.cloudflare.com/turnstile/v0/siteverify",
                  "cf-turnstile-response"),
    "recaptcha": ("https://www.google.com/recaptcha/api/siteverify",
                  "g-recaptcha-response"),
    "hcaptcha": ("https://api.hcaptcha.com/siteverify",
                 "h-captcha-response"),
}

_REP_ORDER = {"ok": 0, "suspicious": 1, "blocked": 2}


def _conf():
    return get_config().get("auth.captcha") or {}


def _secret() -> str:
    return getattr(settings, "SECURITY_CAPTCHA_SECRET", "") or ""


def is_configured() -> bool:
    """True only when CAPTCHA is enabled AND a provider secret is present."""
    return bool(_conf().get("enabled") and _secret())


def provider() -> str:
    name = str(_conf().get("provider", "turnstile")).lower()
    return name if name in _PROVIDERS else "turnstile"


def response_field() -> str:
    return _PROVIDERS[provider()][1]


def is_required(ip: str, failure_count: int = 0) -> bool:
    """Whether the caller must solve a CAPTCHA now."""
    if not is_configured():
        return False
    conf = _conf()
    trigger_after = int(conf.get("trigger_after_failures", 3))
    if failure_count >= trigger_after:
        return True
    wanted = str(conf.get("trigger_on_reputation", "suspicious")).lower()
    status, _ = reputation.status(ip)
    return _REP_ORDER.get(status, 0) >= _REP_ORDER.get(wanted, 1)


def verify(token: str, remote_ip: str = "") -> bool:
    """Validate a CAPTCHA solution with the provider. Returns True when the
    challenge is satisfied (or CAPTCHA is not configured — nothing to check)."""
    if not is_configured():
        return True
    if not token:
        return False

    endpoint = _PROVIDERS[provider()][0]
    try:
        import urllib.parse
        import urllib.request

        data = urllib.parse.urlencode({
            "secret": _secret(),
            "response": token,
            **({"remoteip": remote_ip} if remote_ip else {}),
        }).encode()
        req = urllib.request.Request(endpoint, data=data)
        with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310 (fixed hosts)
            import json

            payload = json.loads(resp.read().decode() or "{}")
        return bool(payload.get("success"))
    except Exception:
        logger.warning("captcha verification error (provider=%s)", provider(),
                       exc_info=True)
        # Availability-first by default: a provider outage shouldn't lock users
        # out. Set auth.captcha.fail_open=false to fail closed instead.
        return bool(_conf().get("fail_open", True))
