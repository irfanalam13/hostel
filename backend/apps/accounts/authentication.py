"""Cookie-aware JWT authentication.

Reads the access token from an httpOnly cookie (set at login), falling back to
the standard ``Authorization: Bearer`` header for non-browser API clients. When
the token is supplied via cookie, CSRF protection is enforced on unsafe methods
exactly like DRF's SessionAuthentication does.
"""
from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware
from rest_framework import exceptions
from rest_framework_simplejwt.authentication import JWTAuthentication
from apps.common.permissions import user_is_hostel_member
from apps.tenants.cache import get_tenant_by_id


class _CSRFCheck(CsrfViewMiddleware):
    def _reject(self, request, reason):
        # Return the reason instead of an HttpResponse so the caller can decide.
        return reason


class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        header = self.get_header(request)
        from_cookie = False

        if header is not None:
            raw_token = self.get_raw_token(header)
        else:
            raw_token = request.COOKIES.get(settings.JWT_AUTH_COOKIE)
            from_cookie = True

        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)
        user = self.get_user(validated_token)
        hostel_code = validated_token.get("hostel_code")
        hostel_id = validated_token.get("hostel_id")

        if not hostel_code or not hostel_id:
            raise exceptions.AuthenticationFailed("Token is missing hostel context.")

        # Password-change detection: tokens embed a fingerprint of the password
        # hash at issue time (pwv). A password change rotates it, so every
        # previously issued token dies here immediately — no waiting for
        # expiry. Tokens minted before this claim existed pass (legacy).
        token_pwv = validated_token.get("pwv")
        if token_pwv is not None and token_pwv != user.password_version:
            raise exceptions.AuthenticationFailed(
                "Session invalidated by a password change. Please sign in again."
            )

        # Resolved through the tenant Redis cache (same one the tenant
        # middleware uses) instead of a per-request Hostel query.
        hostel = get_tenant_by_id(hostel_id)
        if not hostel or hostel.code != hostel_code or not hostel.is_active:
            raise exceptions.AuthenticationFailed("Invalid token hostel context.")

        # Cross-tenant token binding: when the tenant middleware resolved a
        # workspace for this request (subdomain / X-Workspace / header), the
        # token must belong to THAT workspace. A token minted on
        # everest.myhostel.com is unusable against himalayan.myhostel.com even
        # for a user who happens to be a member of both.
        resolved = getattr(request, "tenant", None)
        if resolved is not None and str(resolved.pk) != str(hostel.pk):
            raise exceptions.AuthenticationFailed(
                "This session belongs to a different workspace."
            )

        # Membership guard (superusers bypass inside the helper). Cached in
        # Redis and memoized on the request so the permission classes reuse
        # this same lookup instead of re-querying.
        if not user_is_hostel_member(user, hostel, request=request):
            raise exceptions.AuthenticationFailed("Invalid token hostel membership.")

        request.hostel = hostel

        # Cookie-borne credentials are ambient -> require CSRF on writes.
        if from_cookie:
            self._enforce_csrf(request)

        return (user, validated_token)

    def _enforce_csrf(self, request):
        if request.method in ("GET", "HEAD", "OPTIONS", "TRACE"):
            return
        check = _CSRFCheck(lambda req: None)
        check.process_request(request)
        reason = check.process_view(request, None, (), {})
        if reason:
            raise exceptions.PermissionDenied(f"CSRF Failed: {reason}")


# --- drf-spectacular: describe this custom auth so Swagger/ReDoc render an
# "Authorize" option and stop warning about an unresolved authenticator. The
# scheme advertises both the httpOnly access-token cookie (how the SPA auths)
# and the Bearer header (for non-browser clients). -------------------------
try:
    from drf_spectacular.extensions import OpenApiAuthenticationExtension

    class CookieJWTScheme(OpenApiAuthenticationExtension):
        target_class = "apps.accounts.authentication.CookieJWTAuthentication"
        name = ["cookieAuth", "bearerAuth"]

        def get_security_definition(self, auto_schema):
            return [
                {
                    "type": "apiKey",
                    "in": "cookie",
                    "name": settings.JWT_AUTH_COOKIE,
                    "description": (
                        "httpOnly access-token cookie set by POST /api/auth/login/. "
                        "In Swagger UI, call the login endpoint first — the browser then "
                        "sends this cookie automatically on same-origin 'Try it out' calls."
                    ),
                },
                {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": "For non-browser clients: Authorization: Bearer <access token>.",
                },
            ]
except Exception:  # pragma: no cover - drf-spectacular always present, but be safe
    pass
