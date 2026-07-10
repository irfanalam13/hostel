# apps/accounts/urls.py

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ActivityView,
    CSRFView,
    CookieTokenObtainPairView,
    CookieTokenRefreshView,
    LogoutAllView,
    LogoutView,
    MeView,
    MyPermissionsView,
    PermissionCheckView,
    SessionsView,
    SessionRevokeView,
    SessionVerifyView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    SignupOTPRequestView,
    SignupView,
    UserHostelViewSet,
    UserViewSet,
    ForgotHostelIDView,
)

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="users")
router.register(r"user-hostels", UserHostelViewSet, basename="user_hostels")

urlpatterns = [
    # 🔐 Auth endpoints (cookie-based JWT)
    path("csrf/", CSRFView.as_view(), name="csrf"),
    path("signup/request-otp/", SignupOTPRequestView.as_view(), name="signup_request_otp"),
    path("signup/", SignupView.as_view(), name="signup"),
    path("login/", CookieTokenObtainPairView.as_view(), name="login"),
    path("token/", CookieTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", CookieTokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("logout-all/", LogoutAllView.as_view(), name="logout_all"),
    path("me/", MeView.as_view(), name="me"),
    path("session/verify/", SessionVerifyView.as_view(), name="session_verify"),
    path("permissions/", MyPermissionsView.as_view(), name="my_permissions"),
    path("permissions/check/", PermissionCheckView.as_view(), name="permission_check"),
    path("activity/", ActivityView.as_view(), name="account_activity"),
    path("sessions/", SessionsView.as_view(), name="account_sessions"),
    path("sessions/<int:pk>/", SessionRevokeView.as_view(), name="account_session_revoke"),
    path("password/change/", PasswordChangeView.as_view(), name="password_change"),
    path("password/forgot/", PasswordResetRequestView.as_view(), name="password_reset_request"),
    path("password/reset/", PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("hostel-id/forgot/", ForgotHostelIDView.as_view(), name="forgot_hostel_id"),
]

# Add router endpoints
urlpatterns += router.urls
