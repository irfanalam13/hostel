"""DRF exceptions for the auth-protection layer.

Raised from serializers/views; DRF renders them through the platform's
StandardJSONRenderer, so the client always sees the uniform
``{success, message, data, meta:{code}}`` envelope with the right status.
"""
from rest_framework import status
from rest_framework.exceptions import APIException, Throttled


class ProgressiveLockout(Throttled):
    """429 with a dynamic Retry-After from the progressive-lockout tier."""

    default_detail = "Too many attempts. Please try again later."
    default_code = "auth_locked"


class CaptchaRequired(APIException):
    """403 telling the client to present a CAPTCHA and retry with its token."""

    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Please complete the verification challenge and try again."
    default_code = "captcha_required"


class CaptchaFailed(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Verification challenge failed. Please try again."
    default_code = "captcha_failed"
