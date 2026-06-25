import re

from django.conf import settings

from apps.tenants.models import Hostel

# Hostel codes look like "H-7K2Q9A" (slug). Reject anything else before hitting the DB.
_CODE_RE = re.compile(r"^[A-Za-z0-9_-]{1,40}$")

# Health-check endpoints must stay dependency-free (a liveness probe should not
# touch the DB), so tenant resolution is skipped for them.
_HEALTH_PREFIX = "/health/"


class HostelResolveMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # ✅ Let CORS preflight pass without tenant logic
        if request.method == "OPTIONS":
            return self.get_response(request)

        # ✅ Health checks never resolve a tenant (avoids a DB hit on liveness)
        if request.path.startswith(_HEALTH_PREFIX):
            request.hostel = None
            return self.get_response(request)

        hostel = None

        code = request.headers.get("X-HOSTEL-CODE")
        if code and _CODE_RE.match(code):
            hostel = Hostel.objects.filter(code=code, is_active=True).first()
        elif not code:
            host = request.get_host().split(":")[0]
            parts = host.split(".")
            if len(parts) >= 3:
                sub = parts[0]
                hostel = Hostel.objects.filter(code=sub, is_active=True).first()

        request.hostel = hostel
        return self.get_response(request)    
    


class HostelContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # ✅ Let CORS preflight pass
        if request.method == "OPTIONS":
            return self.get_response(request)

        # ✅ Health checks never resolve a tenant (avoids a DB hit on liveness)
        if request.path.startswith(_HEALTH_PREFIX):
            return self.get_response(request)

        # ✅ If HostelResolveMiddleware already set request.hostel, keep it
        if getattr(request, "hostel", None):
            return self.get_response(request)

        hostel_id = request.headers.get("X-HOSTEL-ID") or request.META.get("HTTP_X_HOSTEL_ID")
        if hostel_id:
            try:
                request.hostel = Hostel.objects.filter(id=hostel_id).first()
            except Exception:
                request.hostel = None

        return self.get_response(request)


# Default CSP suitable for a JSON API. It is intentionally strict: the API
# serves data, not HTML. The browsable DRF UI (dev only) needs inline styles,
# so CSP is skipped when DEBUG is on to avoid breaking it.
_DEFAULT_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
_DEFAULT_PERMISSIONS_POLICY = "geolocation=(), microphone=(), camera=(), payment=()"


class SecurityHeadersMiddleware:
    """Adds defence-in-depth response headers on every request.

    Referrer-Policy and Permissions-Policy are always set. Content-Security-Policy
    is applied outside DEBUG (so it doesn't break the dev browsable API) and is
    overridable via the CSP_POLICY setting. X-Frame-Options / nosniff / HSTS are
    handled by Django's own SecurityMiddleware + settings.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.referrer_policy = getattr(settings, "REFERRER_POLICY", "same-origin")
        self.permissions_policy = getattr(
            settings, "PERMISSIONS_POLICY", _DEFAULT_PERMISSIONS_POLICY
        )
        self.csp = getattr(settings, "CSP_POLICY", _DEFAULT_CSP)
        self.csp_enabled = getattr(settings, "CSP_ENABLED", not settings.DEBUG)

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault("Referrer-Policy", self.referrer_policy)
        response.setdefault("Permissions-Policy", self.permissions_policy)
        if self.csp_enabled and self.csp:
            response.setdefault("Content-Security-Policy", self.csp)
        return response