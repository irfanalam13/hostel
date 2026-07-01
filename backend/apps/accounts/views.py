from django.conf import settings
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.db.models import Q
from django.middleware.csrf import get_token

from rest_framework import serializers, status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.auditlog.models import AuditEvent
from apps.auditlog.services import record_event
from apps.common.permissions import IsOwner

from .cookies import clear_auth_cookies, set_auth_cookies
from .models import User, UserHostel, PasswordResetOTP, SignupOTP
from .serializers import (
    MeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    SignupOTPRequestSerializer,
    SignupSerializer,
    UserCreateSerializer,
    UserHostelSerializer,
    UserSerializer,
    ForgotHostelIDSerializer,
    SecureLoginSerializer,
)
from apps.tenants.models import Hostel


def _hostel_ids_for(user):
    """UUIDs of hostels the given user is actively linked to."""
    return UserHostel.objects.filter(user=user, is_active=True).values_list("hostel_id", flat=True)


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
    def validate(self, attrs):
        attrs = super().validate(attrs)
        request = self.context.get("request")
        generic_error = self.error_messages["invalid_login"]

        hostel = Hostel.objects.filter(code=attrs["hostel_id"], is_active=True).first()
        identifier = attrs["username"]
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
                meta={"hostel_id": attrs["hostel_id"], "identifier": identifier},
            )
            raise serializers.ValidationError({"detail": generic_error})

        if authenticated.role not in dict(User._meta.get_field("role").choices):
            raise serializers.ValidationError({"detail": generic_error})

        refresh = RefreshToken.for_user(authenticated)
        refresh["hostel_id"] = str(hostel.id)
        refresh["hostel_code"] = hostel.code
        refresh["role"] = authenticated.role
        access = refresh.access_token
        access["hostel_id"] = str(hostel.id)
        access["hostel_code"] = hostel.code
        access["role"] = authenticated.role

        self.user = authenticated
        self.hostel = hostel
        return {
            "refresh": str(refresh),
            "access": str(access),
            "hostel_code": hostel.code,
            "user": MeSerializer(authenticated).data,
        }


class CookieTokenObtainPairView(TokenObtainPairView):
    serializer_class = CookieTokenObtainPairSerializer
    throttle_scope = "auth"

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            access = response.data.pop("access", None)
            refresh = response.data.pop("refresh", None)
            user_data = response.data.get("user", {})
            hostel_code = response.data.get("hostel_code")
            set_auth_cookies(response, access=access, refresh=refresh)
            response.data = {"detail": "Login successful", "user": user_data, "hostel_code": hostel_code}
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


class CookieTokenRefreshView(TokenRefreshView):
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
class SignupOTPRequestView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "signup_otp"

    def post(self, request):
        serializer = SignupOTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        import random
        otp_code = f"{random.randint(100000, 999999)}"
        # Only the newest code for this email stays live.
        SignupOTP.objects.filter(email__iexact=email, is_used=False).update(is_used=True)
        SignupOTP.objects.create(email=email, otp=otp_code)

        # Unlike password-reset, the user NEEDS this code to proceed, so we do
        # NOT fail silently: a delivery failure is surfaced as 502 so the SPA can
        # tell the user (and so SMTP/sender misconfig is visible, not hidden).
        try:
            send_mail(
                subject="Verify your email to create your Hostel account",
                message=(
                    "Welcome to Hostel!\n\n"
                    f"Your email verification code (OTP) is: {otp_code}\n\n"
                    "Enter this code on the signup page to create your account. "
                    "It is valid for 15 minutes.\n\n"
                    "If you did not request this, you can safely ignore this email."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
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
class SignupView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "signup"

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        hostel = getattr(user, "_created_hostel", None)
        refresh = RefreshToken.for_user(user)
        if hostel:
            refresh["hostel_id"] = str(hostel.id)
            refresh["hostel_code"] = hostel.code
            refresh["role"] = user.role
            access = refresh.access_token
            access["hostel_id"] = str(hostel.id)
            access["hostel_code"] = hostel.code
            access["role"] = user.role
        else:
            access = refresh.access_token

        response = Response(
            {
                "detail": "Signup successful",
                "user": MeSerializer(user).data,
                "hostel_code": hostel.code if hostel else None,
            },
            status=status.HTTP_201_CREATED,
        )
        set_auth_cookies(response, access=str(access), refresh=str(refresh))
        return response


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = MeSerializer(request.user).data
        hostel = getattr(request, "hostel", None)
        if hostel:
            data["hostel_code"] = hostel.code
            data["hostel_id"] = str(hostel.id)
        return Response(data)


# ---------------------------------------------------------------------------
# Password reset — OTP code, never leaks the token, throttled
# ---------------------------------------------------------------------------
class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "password_reset"

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data.get("email")
        username = serializer.validated_data.get("username")

        user = None
        if email:
            user = User.objects.filter(email__iexact=email, is_active=True).first()
        if not user and username:
            user = User.objects.filter(username__iexact=username, is_active=True).first()

        if user and user.email:
            import random
            otp_code = f"{random.randint(100000, 999999)}"
            # Deactivate old OTPs
            PasswordResetOTP.objects.filter(user=user).update(is_used=True)
            # Create new OTP
            PasswordResetOTP.objects.create(user=user, otp=otp_code)

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


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "password_reset"

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email_or_username = serializer.validated_data["email_or_username"]
        otp_code = serializer.validated_data["otp"]

        user = User.objects.filter(
            Q(email__iexact=email_or_username) | Q(username__iexact=email_or_username), 
            is_active=True
        ).first()

        if not user:
            return Response({"detail": "Invalid credentials or OTP."}, status=status.HTTP_400_BAD_REQUEST)

        otp_obj = PasswordResetOTP.objects.filter(user=user, otp=otp_code, is_used=False).order_by("-created_at").first()
        if not otp_obj or not otp_obj.is_valid():
            return Response({"detail": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)

        otp_obj.is_used = True
        otp_obj.save(update_fields=["is_used"])

        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        record_event(request, action=AuditEvent.Action.UPDATE, actor=user,
                     message="Password reset completed via OTP")
        return Response({"detail": "Password has been reset."})


class ForgotHostelIDView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "password_reset"

    def post(self, request):
        serializer = ForgotHostelIDSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email_or_username = serializer.validated_data["email_or_username"]

        user = User.objects.filter(
            Q(email__iexact=email_or_username) | Q(username__iexact=email_or_username), 
            is_active=True
        ).first()

        if user and user.email:
            user_hostels = UserHostel.objects.filter(user=user, is_active=True).select_related('hostel')
            if user_hostels.exists():
                hostels_info = [f"- {uh.hostel.name} (Hostel ID: {uh.hostel.code})" for uh in user_hostels]
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
