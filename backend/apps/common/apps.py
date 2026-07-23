from django.apps import AppConfig


class CommonConfig(AppConfig):
    name = 'apps.common'

    def ready(self):
        # Optional OpenTelemetry tracing (no-op unless OTEL_ENABLED + packages).
        try:
            from . import otel

            otel.configure()
        except Exception:  # pragma: no cover - never block startup on telemetry
            pass
