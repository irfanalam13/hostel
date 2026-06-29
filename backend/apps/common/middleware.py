import re

from django.conf import settings

from apps.tenants.models import Hostel

# Official backend-generated Hostel IDs look like "HTL-7F4D91A2".
_CODE_RE = re.compile(r"^HTL-[A-Z0-9]{8}$")

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

        code = (request.headers.get("X-HOSTEL-CODE") or "").strip().upper()
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
# Deny every powerful feature — this is a JSON API, it needs none of them.
_DEFAULT_PERMISSIONS_POLICY = (
    "accelerometer=(), autoplay=(), camera=(), display-capture=(), "
    "encrypted-media=(), fullscreen=(), geolocation=(), gyroscope=(), "
    "magnetometer=(), microphone=(), midi=(), payment=(), usb=(), "
    "interest-cohort=(), browsing-topics=()"
)


class SecurityHeadersMiddleware:
    """Adds defence-in-depth response headers on every API response.

    Always set: Referrer-Policy, Permissions-Policy, COOP, CORP and
    X-Permitted-Cross-Domain-Policies. Content-Security-Policy is applied outside
    DEBUG (so it doesn't break the dev browsable API) and is overridable via the
    CSP_POLICY setting. X-Frame-Options / nosniff / HSTS are handled by Django's
    SecurityMiddleware + settings.

    NOTE on CORP: `same-origin` is safe for the cross-origin SPA because its API
    calls use CORS-mode fetch (governed by CORS, not CORP). CORP only blocks
    no-cors embedding of the API as a subresource — which we want to deny.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.referrer_policy = getattr(settings, "REFERRER_POLICY", "same-origin")
        self.permissions_policy = getattr(
            settings, "PERMISSIONS_POLICY", _DEFAULT_PERMISSIONS_POLICY
        )
        self.csp = getattr(settings, "CSP_POLICY", _DEFAULT_CSP)
        self.csp_enabled = getattr(settings, "CSP_ENABLED", not settings.DEBUG)
        self.coop = getattr(settings, "CROSS_ORIGIN_OPENER_POLICY", "same-origin")
        self.corp = getattr(settings, "CROSS_ORIGIN_RESOURCE_POLICY", "same-origin")

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault("Referrer-Policy", self.referrer_policy)
        response.setdefault("Permissions-Policy", self.permissions_policy)
        response.setdefault("Cross-Origin-Opener-Policy", self.coop)
        response.setdefault("Cross-Origin-Resource-Policy", self.corp)
        response.setdefault("X-Permitted-Cross-Domain-Policies", "none")
        if self.csp_enabled and self.csp:
            response.setdefault("Content-Security-Policy", self.csp)
        return response
