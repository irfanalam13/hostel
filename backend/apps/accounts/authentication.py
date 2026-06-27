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
from apps.accounts.models import UserHostel
from apps.tenants.models import Hostel


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

        hostel = Hostel.objects.filter(id=hostel_id, code=hostel_code, is_active=True).first()
        if not hostel:
            raise exceptions.AuthenticationFailed("Invalid token hostel context.")

        if not UserHostel.objects.filter(user=user, hostel=hostel, is_active=True).exists():
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
