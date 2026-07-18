import logging

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from django.core.mail import send_mail
from django.db.models import Q
from django.middleware.csrf import get_token
from django.utils import timezone

from rest_framework import serializers, status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.auditlog.models import AuditEvent
from apps.auditlog.services import record_event
from apps.common import rbac
from apps.common.permissions import IsOwner
from apps.security.throttles import (
    ForgotHostelRateThrottle,
    LoginRateThrottle,
    OTPVerifyRateThrottle,
    PasswordChangeRateThrottle,
    PasswordResetRateThrottle,
    SessionRevokeRateThrottle,
    SignupOTPRateThrottle,
    SignupRateThrottle,
    TokenRefreshRateThrottle,
)

from .cookies import clear_auth_cookies, set_auth_cookies
from .tokens import issue_tokens, remember_me_lifetime
from .models import User, UserHostel, PasswordResetOTP, SignupOTP
from .serializers import (
    ActivityEventSerializer,
    MeSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ProfileUpdateSerializer,
    SignupOTPRequestSerializer,
    SignupSerializer,
    UserCreateSerializer,
    UserHostelSerializer,
    UserSerializer,
    ForgotHostelIDSerializer,
    SecureLoginSerializer,
)
from apps.tenants.models import Hostel

logger = logging.getLogger("apps.accounts")


def _hostel_ids_for(user):
    """UUIDs of hostels the given user is actively linked to."""
    return UserHostel.objects.filter(user=user, is_active=True).values_list("hostel_id", flat=True)


# ---------------------------------------------------------------------------
# OpenAPI helpers — most auth views build their serializer inside post(), so
# drf-spectacular can't infer the request/response shape on its own. These
# lightweight declarations give Swagger real input fields to fill in.
# ---------------------------------------------------------------------------
class DetailSerializer(serializers.Serializer):
    """The `{"detail": "..."}` message body most auth views return."""
    detail = serializers.CharField()


def _detail_response(description):
    """A `{"detail": "..."}` JSON response, the shape almost every auth view
    returns on success/error."""
    return OpenApiResponse(response=DetailSerializer, description=description)


AUTH_TAGS = ["Auth"]


# ---------------------------------------------------------------------------
# User administration — scoped to the requester's hostel(s)
# ---------------------------------------------------------------------------
class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOwner]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return User.objects.all().order_by("username")
        hostel_ids = list(_hostel_ids_for(user))
        return (
            User.objects.filter(hostel_links__hostel_id__in=hostel_ids, hostel_links__is_active=True)
            .distinct()
            .order_by("username")
        )

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return UserCreateSerializer
        return UserSerializer

    def perform_create(self, serializer):
        user = serializer.save()
        hostel = getattr(self.request, "hostel", None)
        if hostel:
            UserHostel.objects.get_or_create(
                user=user, hostel=hostel, defaults={"is_active": True}
            )


class UserHostelViewSet(viewsets.ModelViewSet):
    serializer_class = UserHostelSerializer
    permission_classes = [IsAuthenticated, IsOwner]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return UserHostel.objects.all().order_by("-created_at")
        hostel_ids = list(_hostel_ids_for(user))
        return UserHostel.objects.filter(hostel_id__in=hostel_ids).order_by("-created_at")


# ---------------------------------------------------------------------------
# Cookie-based JWT login / refresh / logout
# ---------------------------------------------------------------------------
class CookieTokenObtainPairSerializer(SecureLoginSerializer):
    """Tenant-scoped login.

    The workspace is determined in priority order:

    1. The tenant resolved by ``TenantResolutionMiddleware`` (subdomain /
       X-Workspace header) — the enterprise flow: authentication always
       happens *inside* an already-resolved workspace.
    2. The ``hostel_id`` (HTL-code) field — the legacy root-domain flow.

    When both are present they must agree — credentials for one workspace can
    never open a session in another. An optional ``portal`` restricts which
    roles may authenticate (a student cannot log in through /admin).
    """

    def validate(self, attrs):
        attrs = super().validate(attrs)
        request = self.context.get("request")
        generic_error = self.error_messages["invalid_login"]

        # --- Enterprise auth protection (Prompt 08) ----------------------- #
        # Pre-auth gate: progressive lockout + CAPTCHA escalation, keyed per
        # IP and per (workspace, identifier). Runs before we touch the DB, so
        # a locked-out source never reaches credential verification.
        from apps.security import auth_guard
        from apps.security.exceptions import CaptchaRequired, ProgressiveLockout

        identity = auth_guard.make_identity(request, attrs["username"])
        gate = auth_guard.check_gate("login", request, identity)
        if gate.blocked:
            raise ProgressiveLockout(wait=gate.retry_after)
        if not auth_guard.verify_captcha_if_required(request, gate):
            raise CaptchaRequired()

        resolved = getattr(request, "tenant", None) or getattr(request, "hostel", None)
        hostel = None
        if attrs["hostel_id"]:
            hostel = Hostel.objects.filter(code=attrs["hostel_id"], is_active=True).first()
            # Cross-tenant guard: an explicit Hostel ID on a workspace host
            # must be that workspace. Fail generically (no oracle).
            if hostel and resolved is not None and hostel.pk != resolved.pk:
                hostel = None
        elif resolved is not None and resolved.is_operational:
            hostel = resolved

        identifier = attrs["username"]
        portal = attrs.get("portal") or ""
        user = None

        if hostel:
            user = (
                User.objects.filter(
                    Q(username__iexact=identifier) | Q(email__iexact=identifier),
                    hostel_links__hostel=hostel,
                    hostel_links__is_active=True,
                    is_active=True,
                )
                .distinct()
                .first()
            )

        authenticated = None
        if user:
            authenticated = authenticate(request=request, username=user.username, password=attrs["password"])

        if not hostel or not user or authenticated is None:
            record_event(
                request,
                action=AuditEvent.Action.LOGIN,
                hostel=hostel,
                actor=user,
                message="Failed login attempt",
                meta={"hostel_id": attrs["hostel_id"], "identifier": identifier,
                      "workspace": getattr(hostel, "slug", None), "portal": portal},
            )
            # Progressive lockout + brute-force/credential-stuffing signals.
            # Surface captcha_required so the SPA can show the widget next try;
            # the message stays generic (no user/hostel enumeration).
            outcome = auth_guard.register_failure(
                "login", request, identity, credential_stuffing=True
            )
            if outcome.blocked:
                raise ProgressiveLockout(wait=outcome.retry_after)
            raise serializers.ValidationError(
                {"detail": generic_error, "captcha_required": outcome.captcha_required}
            )

        if authenticated.role not in dict(User._meta.get_field("role").choices):
            raise serializers.ValidationError({"detail": generic_error})

        # Portal gate: valid credentials, wrong door. Explicit error (the
        # password was right — hiding that would only cause reset loops), and
        # audited as a denied access so escalation attempts are visible.
        if portal and not rbac.portal_allows_role(portal, authenticated.role):
            record_event(
                request,
                action=AuditEvent.Action.ACCESS_DENIED,
                hostel=hostel,
                actor=authenticated,
                message=f"Login blocked: role not allowed on '{portal}' portal",
                meta={"portal": portal, "role": authenticated.role},
            )
            raise serializers.ValidationError(
                {"detail": "This account cannot sign in here. Use your own portal's login page."}
            )

        remember = bool(attrs.get("remember"))
        refresh, access = issue_tokens(
            authenticated, hostel, portal=portal, remember=remember
        )
        update_last_login(None, authenticated)

        # Successful auth clears this identity's progressive-lockout counters.
        auth_guard.register_success("login", request, identity)

        self.user = authenticated
        self.hostel = hostel
        return {
            "refresh": str(refresh),
            "access": str(access),
            "remember": remember,
            "hostel_code": hostel.code,
            "workspace": {
                "username": hostel.slug,
                "url": hostel.workspace_url,
                "status": hostel.status,
                "name": hostel.name,
            },
            "role": authenticated.role,
            "redirect": rbac.default_route_for_role(authenticated.role),
            # MFA architecture prep: flows key off this once a factor ships.
            "mfa_required": bool(getattr(authenticated, "mfa_enabled", False)),
            "user": MeSerializer(authenticated).data,
        }


@extend_schema(
    tags=AUTH_TAGS,
    summary="Log in (cookie-based JWT)",
    description=(
        "Authenticate with Hostel ID + username/email + password. On success "
        "the access & refresh JWTs are set as HttpOnly cookies (not in the body)."
    ),
    request=SecureLoginSerializer,
    responses={
        200: inline_serializer(
            name="LoginResponse",
            fields={
                "detail": serializers.CharField(),
                "user": MeSerializer(),
                "hostel_code": serializers.CharField(),
            },
        ),
        401: _detail_response("Invalid Hostel ID, email, or password."),
    },
)
class CookieTokenObtainPairView(TokenObtainPairView):
    serializer_class = CookieTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            access = response.data.pop("access", None)
            refresh = response.data.pop("refresh", None)
            remember = response.data.pop("remember", False)
            user_data = response.data.get("user", {})
            hostel_code = response.data.get("hostel_code")
            set_auth_cookies(
                response,
                access=access,
                refresh=refresh,
                refresh_max_age=int(remember_me_lifetime().total_seconds()) if remember else None,
            )
            response.data = {
                "detail": "Login successful",
                "user": user_data,
                "hostel_code": hostel_code,
                "workspace": response.data.get("workspace"),
                "role": response.data.get("role"),
                "redirect": response.data.get("redirect"),
                "mfa_required": response.data.get("mfa_required", False),
            }
            success_hostel = Hostel.objects.filter(code=hostel_code).first() if hostel_code else None
            success_user = User.objects.filter(id=user_data.get("id")).first() if user_data.get("id") else None
            record_event(
                request,
                action=AuditEvent.Action.LOGIN,
                hostel=success_hostel,
                actor=success_user,
                message="Login successful",
            )
        return response


@extend_schema(
    tags=AUTH_TAGS,
    summary="Refresh the access token",
    description=(
        "Rotates the access (and refresh) JWT cookies. The refresh token is "
        "read from the HttpOnly cookie; a `refresh` body field is only needed "
        "for non-browser clients that don't use cookies."
    ),
    request=inline_serializer(
        name="TokenRefreshRequest",
        fields={"refresh": serializers.CharField(required=False)},
    ),
    responses={
        200: _detail_response("Token refreshed."),
        401: _detail_response("Invalid or expired refresh token."),
    },
)
class CookieTokenRefreshView(TokenRefreshView):
    throttle_classes = [TokenRefreshRateThrottle]

    def post(self, request, *args, **kwargs):
        refresh = request.COOKIES.get(settings.JWT_AUTH_REFRESH_COOKIE) or request.data.get("refresh")
        if not refresh:
            return Response({"detail": "No refresh token."}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = self.get_serializer(data={"refresh": refresh})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError:
            resp = Response({"detail": "Invalid or expired refresh token."}, status=status.HTTP_401_UNAUTHORIZED)
            return clear_auth_cookies(resp)

        data = serializer.validated_data
        resp = Response({"detail": "Token refreshed"})
        set_auth_cookies(resp, access=data.get("access"), refresh=data.get("refresh"))
        return resp


@extend_schema(
    tags=AUTH_TAGS,
    summary="Log out (clear session cookies)",
    request=inline_serializer(
        name="LogoutRequest",
        fields={"refresh": serializers.CharField(required=False)},
    ),
    responses={200: _detail_response("Logged out.")},
)
class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh = request.COOKIES.get(settings.JWT_AUTH_REFRESH_COOKIE) or request.data.get("refresh")
        if refresh:
            try:
                RefreshToken(refresh).blacklist()
            except Exception:
                pass
        record_event(request, action=AuditEvent.Action.LOGOUT, message="Logout")
        resp = Response({"detail": "Logged out."})
        return clear_auth_cookies(resp)


@extend_schema(
    tags=AUTH_TAGS,
    summary="Get a CSRF token",
    responses={
        200: inline_serializer(
            name="CSRFResponse",
            fields={"detail": serializers.CharField(), "csrftoken": serializers.CharField()},
        )
    },
)
class CSRFView(APIView):
    """Sets the csrftoken cookie so the SPA can echo it back via X-CSRFToken."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        token = get_token(request)
        # Return the token in the body too: when the SPA is served from a
        # different origin it cannot read the (cross-origin) csrftoken cookie
        # via document.cookie, so it reads the value here and echoes it back in
        # the X-CSRFToken header. The cookie itself is still sent automatically.
        return Response({"detail": "CSRF cookie set.", "csrftoken": token})


# ---------------------------------------------------------------------------
# Signup email verification — step 1: email an OTP the SPA confirms on signup
# ---------------------------------------------------------------------------
@extend_schema(
    tags=AUTH_TAGS,
    summary="Signup step 1 — request an email verification OTP",
    request=SignupOTPRequestSerializer,
    responses={
        200: _detail_response("A verification code has been sent to your email."),
        502: _detail_response("Could not send the verification email."),
    },
)
class SignupOTPRequestView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [SignupOTPRateThrottle]

    def post(self, request):
        serializer = SignupOTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        # Enumeration signal: many distinct emails probed from one IP.
        from apps.security import auth_guard

        auth_guard.note_enumeration(request, email)

        import random
        otp_code = f"{random.randint(100000, 999999)}"
        # Only the newest code for this email stays live.
        SignupOTP.objects.filter(email__iexact=email, is_used=False).update(is_used=True)
        SignupOTP.objects.create(email=email, otp=otp_code)

        # Send the email off the request cycle: enqueue for the Celery worker so a
        # slow/unreachable SMTP host can never block, hang, or drop this request.
        # Delivery (with retries) happens in the worker. Only a broker failure —
        # i.e. we can't even queue the work — surfaces as 502, so misconfig stays
        # visible instead of being hidden.
        from .tasks import send_signup_otp_email
        from apps.common.tasking import dispatch_task

        try:
            dispatch_task(send_signup_otp_email, email, otp_code)
        except Exception:
            return Response(
                {"detail": "Could not send the verification email. Please try again later."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        record_event(request, action=AuditEvent.Action.CREATE,
                     message="Signup verification OTP requested", meta={"email": email})
        return Response({"detail": "A verification code has been sent to your email."})


# ---------------------------------------------------------------------------
# Signup (creates owner + hostel) — also issues cookie session
# ---------------------------------------------------------------------------
@extend_schema(
    tags=AUTH_TAGS,
    summary="Signup step 2 — create owner + hostel",
    description="Creates the owner account and its hostel, then sets session cookies.",
    request=SignupSerializer,
    responses={
        201: inline_serializer(
            name="SignupResponse",
            fields={
                "detail": serializers.CharField(),
                "user": MeSerializer(),
                "hostel_code": serializers.CharField(),
            },
        ),
    },
)
class SignupView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [SignupRateThrottle]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        hostel = getattr(user, "_created_hostel", None)

        # Email the freshly-minted Hostel ID to the owner (off the request cycle,
        # same pattern as the signup OTP — SMTP latency must never block signup).
        # A broker hiccup here shouldn't fail an otherwise-successful signup, so
        # enqueue best-effort and let the account creation stand regardless.
        if hostel and user.email:
            from .tasks import send_hostel_id_email
            from apps.common.tasking import dispatch_task

            try:
                dispatch_task(send_hostel_id_email, user.email, user.username, hostel.name, hostel.code)
            except Exception:
                logger.warning("Could not enqueue Hostel ID email for %s", user.email)

        if hostel:
            refresh, access = issue_tokens(user, hostel, portal="admin")
        else:
            refresh = RefreshToken.for_user(user)
            access = refresh.access_token

        response = Response(
            {
                "detail": "Signup successful",
                "user": MeSerializer(user).data,
                "hostel_code": hostel.code if hostel else None,
                "workspace": {
                    "username": hostel.slug,
                    "url": hostel.workspace_url,
                    "status": hostel.status,
                } if hostel else None,
            },
            status=status.HTTP_201_CREATED,
        )
        set_auth_cookies(response, access=str(access), refresh=str(refresh))
        return response


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def _me_payload(self, request):
        data = MeSerializer(request.user).data
        # Platform staff are distinguished by Django's is_superuser flag, not a
        # tenant role. Surface it as the SUPER_ADMIN role so the frontend can
        # gate the platform (Super Admin) subscription panel on it.
        if getattr(request.user, "is_superuser", False):
            data["role"] = "SUPER_ADMIN"
        data["is_superuser"] = bool(getattr(request.user, "is_superuser", False))
        hostel = getattr(request, "hostel", None)
        if hostel:
            data["hostel_code"] = hostel.code
            data["hostel_id"] = str(hostel.id)
        return data

    @extend_schema(
        tags=AUTH_TAGS,
        summary="Get the current user",
        responses={200: MeSerializer},
    )
    def get(self, request):
        return Response(self._me_payload(request))

    @extend_schema(
        tags=AUTH_TAGS,
        summary="Update my profile (name + email)",
        request=ProfileUpdateSerializer,
        responses={200: MeSerializer},
    )
    def patch(self, request):
        """Self-service profile edit (display name + email)."""
        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        record_event(
            request,
            action=AuditEvent.Action.UPDATE,
            actor=request.user,
            message="Profile updated",
            meta={"fields": list(serializer.validated_data.keys())},
        )
        return Response(self._me_payload(request))


class PasswordChangeView(APIView):
    """Authenticated password change. Tokens embed a password-version
    fingerprint (pwv), so changing the password invalidates every previously
    issued token — all other devices are forced to sign in again. This device
    stays signed in: fresh tokens (with the new pwv) are set on the response."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [PasswordChangeRateThrottle]

    @extend_schema(
        tags=AUTH_TAGS,
        summary="Change my password (signs out all other devices)",
        request=PasswordChangeSerializer,
        responses={200: _detail_response("Your password has been changed.")},
    )
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        record_event(request, action=AuditEvent.Action.UPDATE, actor=user,
                     message="Password changed (other sessions invalidated)")

        response = Response(
            {"detail": "Your password has been changed. Other devices were signed out."}
        )
        # Keep THIS session alive across the pwv rotation.
        hostel = getattr(request, "hostel", None)
        if hostel is not None:
            refresh, access = issue_tokens(user, hostel)
            set_auth_cookies(response, access=str(access), refresh=str(refresh))
        return response


class LogoutAllView(APIView):
    """Revoke every outstanding refresh token for the current user (sign out of
    all devices), then clear this device's cookies too."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=AUTH_TAGS,
        summary="Sign out of all devices",
        request=None,
        responses={200: _detail_response("Signed out of all devices.")},
    )
    def post(self, request):
        try:
            from rest_framework_simplejwt.token_blacklist.models import (
                BlacklistedToken,
                OutstandingToken,
            )

            for token in OutstandingToken.objects.filter(user=request.user):
                BlacklistedToken.objects.get_or_create(token=token)
        except Exception:
            # Blacklist app unavailable — still clear this session below.
            pass
        record_event(
            request,
            action=AuditEvent.Action.LOGOUT,
            actor=request.user,
            message="Signed out of all sessions",
        )
        resp = Response({"detail": "Signed out of all devices."})
        return clear_auth_cookies(resp)


# ---------------------------------------------------------------------------
# Account activity timeline — read-only view of the user's own audit trail
# ---------------------------------------------------------------------------
class ActivityView(APIView):
    """Recent security-relevant events for the signed-in user (logins, profile
    and password changes, etc.), newest first. Read-only, always scoped to
    ``request.user`` — powered by the existing AuditEvent log."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=AUTH_TAGS,
        summary="My recent account activity",
        responses={200: ActivityEventSerializer(many=True)},
    )
    def get(self, request):
        try:
            limit = int(request.query_params.get("limit", 20))
        except (TypeError, ValueError):
            limit = 20
        limit = max(1, min(limit, 100))
        events = AuditEvent.objects.filter(actor=request.user).order_by("-created_at")[:limit]
        return Response(ActivityEventSerializer(events, many=True).data)


# ---------------------------------------------------------------------------
# Active sessions — list/revoke live refresh tokens (devices)
# ---------------------------------------------------------------------------
def _friendly_device(user_agent):
    """Best-effort 'Browser · OS' label from a User-Agent string. Intentionally
    coarse — enough to help a user recognise a device, not fingerprint it."""
    ua = (user_agent or "").lower()
    if "android" in ua:
        os_name = "Android"
    elif "iphone" in ua or "ipad" in ua or "ios" in ua:
        os_name = "iOS"
    elif "windows" in ua:
        os_name = "Windows"
    elif "mac os" in ua or "macintosh" in ua:
        os_name = "macOS"
    elif "linux" in ua:
        os_name = "Linux"
    else:
        os_name = ""

    if "edg" in ua:
        browser = "Edge"
    elif "chrome" in ua or "crios" in ua:
        browser = "Chrome"
    elif "firefox" in ua or "fxios" in ua:
        browser = "Firefox"
    elif "safari" in ua:
        browser = "Safari"
    else:
        browser = ""

    label = " · ".join(p for p in (browser, os_name) if p)
    return label or "Unknown device"


def _current_refresh_jti(request):
    """jti of the refresh token backing THIS request's session, or None."""
    raw = request.COOKIES.get(settings.JWT_AUTH_REFRESH_COOKIE) or request.data.get("refresh")
    if not raw:
        return None
    try:
        return RefreshToken(raw)["jti"]
    except Exception:
        return None


class SessionsView(APIView):
    """List the account's live sessions. With ROTATE_REFRESH_TOKENS +
    BLACKLIST_AFTER_ROTATION, the non-blacklisted, non-expired OutstandingTokens
    are effectively one entry per active device. The current session is flagged
    and carries a device label parsed from this request's User-Agent."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=AUTH_TAGS,
        summary="List my active sessions (devices)",
        responses={
            200: inline_serializer(
                name="SessionListItem",
                fields={
                    "id": serializers.IntegerField(),
                    "created_at": serializers.DateTimeField(),
                    "expires_at": serializers.DateTimeField(),
                    "current": serializers.BooleanField(),
                    "device": serializers.CharField(),
                },
                many=True,
            )
        },
    )
    def get(self, request):
        try:
            from rest_framework_simplejwt.token_blacklist.models import (
                BlacklistedToken,
                OutstandingToken,
            )
        except Exception:
            return Response([])

        current_jti = _current_refresh_jti(request)
        current_device = _friendly_device(request.META.get("HTTP_USER_AGENT", ""))
        blacklisted = set(
            BlacklistedToken.objects.filter(token__user=request.user).values_list(
                "token__jti", flat=True
            )
        )

        sessions = []
        tokens = OutstandingToken.objects.filter(
            user=request.user, expires_at__gt=timezone.now()
        ).order_by("-created_at")
        for token in tokens:
            if token.jti in blacklisted:
                continue
            is_current = current_jti is not None and token.jti == current_jti
            sessions.append(
                {
                    "id": token.id,
                    "created_at": token.created_at,
                    "expires_at": token.expires_at,
                    "current": is_current,
                    "device": current_device if is_current else "",
                }
            )
        return Response(sessions)


class SessionRevokeView(APIView):
    """Revoke a single session by OutstandingToken id (sign that device out).
    Refuses to revoke the current session — use logout for that so the cookies
    are cleared too."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [SessionRevokeRateThrottle]

    @extend_schema(
        tags=AUTH_TAGS,
        summary="Revoke a single session (sign a device out)",
        responses={
            200: _detail_response("That device has been signed out."),
            400: _detail_response("This is your current session — use sign out instead."),
            404: _detail_response("Session not found."),
        },
    )
    def delete(self, request, pk):
        try:
            from rest_framework_simplejwt.token_blacklist.models import (
                BlacklistedToken,
                OutstandingToken,
            )
        except Exception:
            return Response(
                {"detail": "Session management is unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        token = OutstandingToken.objects.filter(id=pk, user=request.user).first()
        if not token:
            return Response({"detail": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

        if token.jti == _current_refresh_jti(request):
            return Response(
                {"detail": "This is your current session — use sign out instead."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        BlacklistedToken.objects.get_or_create(token=token)
        record_event(
            request,
            action=AuditEvent.Action.LOGOUT,
            actor=request.user,
            message="Revoked another session",
        )
        return Response({"detail": "That device has been signed out."})


# ---------------------------------------------------------------------------
# Password reset — OTP code, never leaks the token, throttled
# ---------------------------------------------------------------------------
@extend_schema(
    tags=AUTH_TAGS,
    summary="Request a password-reset OTP",
    request=PasswordResetRequestSerializer,
    responses={200: _detail_response("If the account exists, a password reset OTP has been sent.")},
)
class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PasswordResetRateThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data.get("email")
        username = serializer.validated_data.get("username")

        # Enumeration signal (response stays uniform regardless).
        from apps.security import auth_guard

        auth_guard.note_enumeration(request, email or username or "")

        # Workspace-aware: on a workspace host the reset only ever finds THAT
        # workspace's members — never a global account search. The root-domain
        # flow (no tenant resolved) keeps the legacy global lookup.
        base_qs = User.objects.filter(is_active=True)
        tenant = getattr(request, "tenant", None) or getattr(request, "hostel", None)
        if tenant is not None:
            base_qs = base_qs.filter(
                hostel_links__hostel=tenant, hostel_links__is_active=True
            ).distinct()

        user = None
        if email:
            user = base_qs.filter(email__iexact=email).first()
        if not user and username:
            user = base_qs.filter(username__iexact=username).first()

        if user and user.email:
            import random
            otp_code = f"{random.randint(100000, 999999)}"
            # Deactivate old OTPs
            PasswordResetOTP.objects.filter(user=user).update(is_used=True)
            # Create new OTP
            PasswordResetOTP.objects.create(user=user, otp=otp_code)

            # Enqueue for the Celery worker so SMTP latency never blocks this
            # request. On a broker failure fall back to the old synchronous
            # silent send — never an error response here, or the different
            # status would leak whether the account exists.
            from .tasks import send_password_reset_otp_email
            from apps.common.tasking import dispatch_task

            try:
                dispatch_task(send_password_reset_otp_email, user.email, otp_code)
            except Exception:
                try:
                    send_mail(
                        subject="Reset your Hostel account password",
                        message=(
                            "We received a request to reset your password.\n\n"
                            f"Your One-Time Password (OTP) is: {otp_code}\n\n"
                            "This OTP is valid for 15 minutes. "
                            "If you did not request this, you can safely ignore this email."
                        ),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=True,
                    )
                except Exception:
                    pass
            record_event(request, action=AuditEvent.Action.UPDATE, actor=user,
                         message="Password reset OTP requested")

        # Always the same response — no account enumeration, no token leak.
        return Response({"detail": "If the account exists, a password reset OTP has been sent."})


@extend_schema(
    tags=AUTH_TAGS,
    summary="Confirm password reset with OTP",
    request=PasswordResetConfirmSerializer,
    responses={
        200: _detail_response("Password has been reset."),
        400: _detail_response("Invalid or expired OTP."),
    },
)
class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [OTPVerifyRateThrottle]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email_or_username = serializer.validated_data["email_or_username"]
        otp_code = serializer.validated_data["otp"]

        # Progressive lockout on OTP verification (brute-forcing a 6-digit code).
        from apps.security import auth_guard
        from apps.security.exceptions import ProgressiveLockout

        identity = auth_guard.make_identity(request, email_or_username)
        gate = auth_guard.check_gate("otp_verify", request, identity)
        if gate.blocked:
            raise ProgressiveLockout(wait=gate.retry_after)

        # Same workspace scoping as the request step.
        user_qs = User.objects.filter(
            Q(email__iexact=email_or_username) | Q(username__iexact=email_or_username),
            is_active=True
        )
        tenant = getattr(request, "tenant", None) or getattr(request, "hostel", None)
        if tenant is not None:
            user_qs = user_qs.filter(
                hostel_links__hostel=tenant, hostel_links__is_active=True
            ).distinct()
        user = user_qs.first()

        if not user:
            auth_guard.register_failure("otp_verify", request, identity)
            return Response({"detail": "Invalid credentials or OTP."}, status=status.HTTP_400_BAD_REQUEST)

        otp_obj = PasswordResetOTP.objects.filter(user=user, otp=otp_code, is_used=False).order_by("-created_at").first()
        if not otp_obj or not otp_obj.is_valid():
            auth_guard.register_failure("otp_verify", request, identity)
            return Response({"detail": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)

        otp_obj.is_used = True
        otp_obj.save(update_fields=["is_used"])

        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        auth_guard.register_success("otp_verify", request, identity)
        record_event(request, action=AuditEvent.Action.UPDATE, actor=user,
                     message="Password reset completed via OTP")
        return Response({"detail": "Password has been reset."})


@extend_schema(
    tags=AUTH_TAGS,
    summary="Recover forgotten Hostel ID(s) by email",
    request=ForgotHostelIDSerializer,
    responses={200: _detail_response("If the account exists, the Hostel ID details have been sent to your email.")},
)
class ForgotHostelIDView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ForgotHostelRateThrottle]

    def post(self, request):
        serializer = ForgotHostelIDSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email_or_username = serializer.validated_data["email_or_username"]

        from apps.security import auth_guard

        auth_guard.note_enumeration(request, email_or_username)

        user = User.objects.filter(
            Q(email__iexact=email_or_username) | Q(username__iexact=email_or_username), 
            is_active=True
        ).first()

        if user and user.email:
            user_hostels = UserHostel.objects.filter(user=user, is_active=True).select_related('hostel')
            if user_hostels.exists():
                hostels_info = [f"- {uh.hostel.name} (Hostel ID: {uh.hostel.code})" for uh in user_hostels]
                # Enqueue for the Celery worker (SMTP off the request path);
                # fall back to the old synchronous silent send on a broker
                # failure — the response must stay uniform (no enumeration).
                from .tasks import send_hostel_id_list_email
                from apps.common.tasking import dispatch_task

                try:
                    dispatch_task(send_hostel_id_list_email, user.email, user.username, hostels_info)
                except Exception:
                    try:
                        send_mail(
                            subject="Your Hostel ID Details",
                            message=(
                                f"Hello {user.username},\n\n"
                                "You requested your Hostel ID(s) associated with this account.\n\n"
                                "Here is your Hostel ID list:\n"
                                + "\n".join(hostels_info) + "\n\n"
                                "You can use these Hostel IDs to log in or manage your hostels.\n\n"
                                "If you did not request this, you can safely ignore this email."
                            ),
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[user.email],
                            fail_silently=True,
                        )
                    except Exception:
                        pass
                record_event(request, action=AuditEvent.Action.UPDATE, actor=user,
                             message="Forgot Hostel ID details requested")

        return Response({"detail": "If the account exists, the Hostel ID details have been sent to your email."})


# ---------------------------------------------------------------------------
# Session verification + RBAC introspection (Prompt 02)
# ---------------------------------------------------------------------------
class SessionVerifyView(APIView):
    """Verify the current session in one round-trip: authentication, tenant
    binding, membership and workspace status were all enforced by the
    authentication stack before this handler runs — reaching it IS the proof.
    Returns the session's user + workspace + role + default route so frontend
    route guards can hydrate from a single call."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=AUTH_TAGS,
        summary="Verify the current session (user + workspace + role)",
        responses={
            200: inline_serializer(
                name="SessionVerifyResponse",
                fields={
                    "authenticated": serializers.BooleanField(),
                    "user": MeSerializer(),
                    "role": serializers.CharField(),
                    "redirect": serializers.CharField(),
                    "workspace": serializers.DictField(),
                },
            ),
            401: _detail_response("No valid session."),
        },
    )
    def get(self, request):
        hostel = getattr(request, "hostel", None)
        role = getattr(request.user, "role", "")
        return Response({
            "authenticated": True,
            "user": MeSerializer(request.user).data,
            "role": role,
            "redirect": rbac.default_route_for_role(role),
            "workspace": {
                "username": hostel.slug,
                "url": hostel.workspace_url,
                "name": hostel.name,
                "status": hostel.status,
            } if hostel else None,
        })


class MyPermissionsView(APIView):
    """The caller's effective permissions in the resolved workspace —
    role defaults merged with any per-workspace overrides
    (``Hostel.settings["permissions"]["roles"]``), Redis-cached."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=AUTH_TAGS,
        summary="My effective permissions in this workspace",
        responses={
            200: inline_serializer(
                name="MyPermissionsResponse",
                fields={
                    "role": serializers.CharField(),
                    "permissions": serializers.ListField(child=serializers.CharField()),
                },
            )
        },
    )
    def get(self, request):
        perms = rbac.user_permissions(request.user, getattr(request, "hostel", None), request=request)
        return Response({
            "role": getattr(request.user, "role", ""),
            "permissions": sorted(perms),
        })


class PermissionCheckView(APIView):
    """Point check: does the caller hold a specific permission here?
    ``GET /auth/permissions/check/?permission=residents.create``"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=AUTH_TAGS,
        summary="Check one permission in this workspace",
        responses={
            200: inline_serializer(
                name="PermissionCheckResponse",
                fields={
                    "permission": serializers.CharField(),
                    "allowed": serializers.BooleanField(),
                },
            ),
            400: _detail_response("Missing ?permission= parameter."),
        },
    )
    def get(self, request):
        permission = (request.query_params.get("permission") or "").strip()
        if not permission:
            return Response(
                {"detail": "Missing ?permission= parameter."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        allowed = rbac.user_has_permission(
            request.user, getattr(request, "hostel", None), permission, request=request
        )
        return Response({"permission": permission, "allowed": allowed})
