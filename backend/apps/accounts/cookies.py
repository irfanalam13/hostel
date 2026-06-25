"""Helpers for setting/clearing the httpOnly JWT cookies."""
from django.conf import settings

SIMPLE_JWT = settings.SIMPLE_JWT


def _common_kwargs():
    return dict(
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite=settings.JWT_COOKIE_SAMESITE,
        domain=settings.JWT_COOKIE_DOMAIN,
        path="/",
    )


def set_auth_cookies(response, access=None, refresh=None):
    kwargs = _common_kwargs()
    if access:
        response.set_cookie(
            settings.JWT_AUTH_COOKIE,
            access,
            max_age=int(SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
            **kwargs,
        )
    if refresh:
        response.set_cookie(
            settings.JWT_AUTH_REFRESH_COOKIE,
            refresh,
            max_age=int(SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
            **kwargs,
        )
    return response


def clear_auth_cookies(response):
    for name in (settings.JWT_AUTH_COOKIE, settings.JWT_AUTH_REFRESH_COOKIE):
        response.delete_cookie(
            name,
            path="/",
            domain=settings.JWT_COOKIE_DOMAIN,
            samesite=settings.JWT_COOKIE_SAMESITE,
        )
    return response
