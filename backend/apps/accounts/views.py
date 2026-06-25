from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db.models import Q
from django.middleware.csrf import get_token
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.auditlog.models import AuditEvent
from apps.auditlog.services import record_event
from apps.common.permissions import IsOwner

from .cookies import clear_auth_cookies, set_auth_cookies
from .models import User, UserHostel
from .serializers import (
    MeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    SignupSerializer,
    UserCreateSerializer,
    UserHostelSerializer,
    UserSerializer,
)


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
class CookieTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = MeSerializer(self.user).data
        return data


class CookieTokenObtainPairView(TokenObtainPairView):
    serializer_class = CookieTokenObtainPairSerializer
    throttle_scope = "auth"

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            access = response.data.pop("access", None)
            refresh = response.data.pop("refresh", None)
            user_data = response.data.get("user", {})
            set_auth_cookies(response, access=access, refresh=refresh)
            response.data = {"detail": "Login successful", "user": user_data}
            record_event(
                request,
                action=AuditEvent.Action.LOGIN,
                message=f"Login: {request.data.get('username', '')}",
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

        response = Response(
            {
                "detail": "Signup successful",
                "user": MeSerializer(user).data,
                "hostel_code": hostel.code if hostel else None,
            },
            status=status.HTTP_201_CREATED,
        )
        set_auth_cookies(response, access=str(refresh.access_token), refresh=str(refresh))
        return response


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(MeSerializer(request.user).data)


# ---------------------------------------------------------------------------
# Password reset — emailed link, never leaks the token, throttled
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
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
            try:
                send_mail(
                    subject="Reset your Hostel account password",
                    message=(
                        "We received a request to reset your password.\n\n"
                        f"Reset link: {reset_url}\n\n"
                        "If you did not request this, you can safely ignore this email."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=True,
                )
            except Exception:
                pass
            record_event(request, action=AuditEvent.Action.UPDATE, actor=user,
                         message="Password reset requested")

        # Always the same response — no account enumeration, no token leak.
        return Response({"detail": "If the account exists, password reset instructions have been sent."})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "password_reset"

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            uid = force_str(urlsafe_base64_decode(serializer.validated_data["uid"]))
            user = User.objects.get(pk=uid, is_active=True)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"detail": "Invalid reset link."}, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, serializer.validated_data["token"]):
            return Response({"detail": "Invalid or expired reset token."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        record_event(request, action=AuditEvent.Action.UPDATE, actor=user,
                     message="Password reset completed")
        return Response({"detail": "Password has been reset."})
