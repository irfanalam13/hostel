from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import HasHostelContext, IsSuperUser

from .models import AnalyticsEvent
from .rollup import build_trends
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
        # Geo from the CDN edge (Cloudflare); never trusted from the client.
        country = (request.META.get("HTTP_CF_IPCOUNTRY", "") or "")[:2].upper()
        if country in ("XX", "T1"):  # CF placeholders for unknown/Tor
            country = ""

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
                country=country,
            )
            for ev in data["events"][:MAX_BATCH]
        ]
        AnalyticsEvent.objects.bulk_create(rows)
        return Response({"accepted": len(rows)})


class ReportView(APIView):
    """Aggregated PWA metrics for the active hostel (super admin only).

    PWA telemetry (install/cache/error rates, device mix) is a platform-operator
    concern, not hostel business — so it is walled off from tenant owners and
    surfaced only on the super-admin dashboard."""

    permission_classes = [HasHostelContext, IsSuperUser]

    def get(self, request):
        try:
            days = int(request.query_params.get("days", 30))
        except (TypeError, ValueError):
            days = 30
        days = max(1, min(days, 365))
        return Response(build_report(request.hostel, days=days))


class TrendsView(APIView):
    """Historical event trends served from the durable rollup pipeline.

    Unlike ReportView (live, transactional-table scan over a short window), this
    reads pre-aggregated ``EventDailyRollup`` rows, so it stays cheap over long
    windows and survives raw-event retention pruning. Super-admin only.
    """

    permission_classes = [HasHostelContext, IsSuperUser]

    def get(self, request):
        try:
            days = int(request.query_params.get("days", 90))
        except (TypeError, ValueError):
            days = 90
        days = max(1, min(days, 730))
        granularity = request.query_params.get("granularity", "day")
        return Response(build_trends(request.hostel, days=days, granularity=granularity))
