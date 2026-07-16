"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Opt-in OpenTelemetry tracing (no-op unless OTEL_ENABLED + deps present).
from config.otel import init_tracing  # noqa: E402

init_tracing()

application = get_asgi_application()
