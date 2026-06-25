"""Custom response returned by django-axes when an account/IP is locked out."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer


def lockout_response(request, credentials=None, *args, **kwargs):
    resp = Response(
        {"detail": "Too many failed login attempts. Please try again later."},
        status=status.HTTP_429_TOO_MANY_REQUESTS,
    )
    resp.accepted_renderer = JSONRenderer()
    resp.accepted_media_type = "application/json"
    resp.renderer_context = {}
    resp.render()
    return resp
