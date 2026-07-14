"""Auth for the internal service->gateway callbacks.

Tool endpoints and conversation-context/complete callbacks are called by the
ML_hostel service, not by a browser, so they authenticate with the context
token (Bearer) rather than the session cookie. ``IsMlContext`` verifies the
token and hangs the decoded claims off ``request.ml_ctx`` for the view.
"""
import jwt
from rest_framework.permissions import BasePermission

from .tokens import verify_context_token


class IsMlContext(BasePermission):
    message = "Invalid or expired AI service token."

    def has_permission(self, request, view):
        auth = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth.startswith("Bearer "):
            return False
        token = auth[7:].strip()
        try:
            ctx = verify_context_token(token)
        except jwt.PyJWTError:
            return False
        request.ml_ctx = ctx
        return True
