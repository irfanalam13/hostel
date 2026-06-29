from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import HasHostelContext, IsOwnerOrManager

from .models import AnalyticsEvent
from .serializers import CollectSerializer
from .services import build_report, parse_user_agent

# Cap how many events one request may insert (matches serializer max_length).
MAX_BATCH = 200


class CollectView(APIView):
    """Ingest a batch of telemetry events from the client.

    Device type / browser are derived server-side from the User-Agent so the
    client can't spoof them and we don't trust client-reported values.
    """

    permission_classes = [IsAuthenticated, HasHostelContext]

    def post(self, request):
        serializer = CollectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        ua = request.META.get("HTTP_USER_AGENT", "")
        device_type, browser, platform = parse_user_agent(ua)
        app_version = data.get("app_version", "")[:40]
        sw_version = data.get("sw_version", "")[:40]

        rows = [
            AnalyticsEvent(
                hostel=request.hostel,
                user=request.user,
                event_type=ev["event_type"],
                name=str(ev.get("name", ""))[:200],
                value=ev.get("value", 0) or 0,
                occurred_at=ev.get("occurred_at"),
                meta=ev.get("meta", {}) or {},
                device_type=device_type,
                browser=browser,
                platform=platform,
                app_version=app_version,
                sw_version=sw_version,
            )
            for ev in data["events"][:MAX_BATCH]
        ]
        AnalyticsEvent.objects.bulk_create(rows)
        return Response({"accepted": len(rows)})


class ReportView(APIView):
    """Aggregated PWA metrics for the active hostel (owner/manager only)."""

    permission_classes = [HasHostelContext, IsOwnerOrManager]

    def get(self, request):
        try:
            days = int(request.query_params.get("days", 30))
        except (TypeError, ValueError):
            days = 30
        days = max(1, min(days, 365))
        return Response(build_report(request.hostel, days=days))
