# apps/accounts/urls.py

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CSRFView,
    CookieTokenObtainPairView,
    CookieTokenRefreshView,
    LogoutView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
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
    path("signup/", SignupView.as_view(), name="signup"),
    path("login/", CookieTokenObtainPairView.as_view(), name="login"),
    path("token/", CookieTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", CookieTokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path("password/forgot/", PasswordResetRequestView.as_view(), name="password_reset_request"),
    path("password/reset/", PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("hostel-id/forgot/", ForgotHostelIDView.as_view(), name="forgot_hostel_id"),
]

# Add router endpoints
urlpatterns += router.urls
