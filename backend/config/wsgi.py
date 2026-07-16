"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Opt-in OpenTelemetry tracing (no-op unless OTEL_ENABLED + deps present).
from config.otel import init_tracing  # noqa: E402

init_tracing()

application = get_wsgi_application()
