"""Tenant-scoped JWT issuing.

Every token this platform issues belongs to exactly one workspace. The claims:

  hostel_id / hostel_code — the tenant the session is bound to (legacy names,
                            consumed everywhere since Phase 1)
  workspace               — the tenant's permanent workspace username (slug)
  role                    — the user's role at login time (informational; the
                            DB role is always re-checked for authorization)
  pwv                     — password-version fingerprint; a password change
                            rotates it, invalidating every earlier token
  portal                  — which login surface issued the session

``CookieJWTAuthentication`` enforces hostel/workspace binding and pwv on every
request, so none of these are trust-the-client values.
"""
from datetime import timedelta

from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken


def remember_me_lifetime() -> timedelta:
    return timedelta(days=int(getattr(settings, "REMEMBER_ME_REFRESH_DAYS", 30)))


def issue_tokens(user, hostel, *, portal: str = "", remember: bool = False):
    """Create a (refresh, access) pair bound to the given workspace.

    ``remember`` extends the *refresh* token lifetime (the access token stays
    short-lived regardless — "remember me" means fewer re-logins, not a
    longer-lived credential on every request).
    """
    refresh = RefreshToken.for_user(user)

    claims = {
        "hostel_id": str(hostel.id),
        "hostel_code": hostel.code,
        "workspace": hostel.slug or "",
        "role": user.role,
        "pwv": user.password_version,
    }
    if portal:
        claims["portal"] = portal

    for key, value in claims.items():
        refresh[key] = value

    if remember:
        refresh.set_exp(lifetime=remember_me_lifetime())

    access = refresh.access_token
    for key, value in claims.items():
        access[key] = value

    return refresh, access
