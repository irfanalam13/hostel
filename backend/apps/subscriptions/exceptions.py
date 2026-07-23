"""Structured entitlement errors.

Both carry a machine ``code`` and enough context for the frontend upgrade
experience (Module 12) to render a meaningful "upgrade to unlock" modal instead
of a generic failure. The ``detail`` dict includes a readable ``detail`` string
so the standard response envelope surfaces a good ``message`` too.
"""
from rest_framework.exceptions import APIException


class FeatureNotAvailable(APIException):
    status_code = 403
    default_code = "feature_not_available"

    def __init__(self, feature_key: str, feature_name: str = "", message: str = ""):
        label = feature_name or feature_key
        detail = {
            "code": self.default_code,
            "feature": feature_key,
            "feature_name": label,
            "detail": message or f"{label} is not included in your current plan.",
        }
        super().__init__(detail=detail)


class PlanLimitExceeded(APIException):
    status_code = 403
    default_code = "plan_limit_reached"

    def __init__(self, limit_key: str, limit_name: str, current, maximum, message: str = ""):
        detail = {
            "code": self.default_code,
            "limit": limit_key,
            "limit_name": limit_name,
            "current": current,
            "max": maximum,
            "detail": message
            or (
                f"You've reached your plan's limit of {maximum} "
                f"{limit_name.lower()}. Upgrade to add more."
            ),
        }
        super().__init__(detail=detail)
