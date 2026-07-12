"""Super-Admin security operations API (mounted under /api/platform/security/).

The backend for the enterprise security-administration dashboard: live threat
monitoring, the event feed, dynamic IP-rule and config-rule editing (hot
reload, no redeploy), reputation control, security reports, and the emergency
kill switch. Every endpoint is gated by ``IsPlatformAdmin`` (Django
``is_superuser``) and every mutation is audited.

All configuration mutation flows through ``SecuritySetting`` / ``IPRule`` rows,
whose signals bump the config generation — so a change here propagates to every
container within seconds without a restart (live configuration reload).
"""
import logging

from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auditlog.models import AuditEvent
from apps.auditlog.services import record_event
from apps.subscriptions.permissions import IsPlatformAdmin

from . import conf, reports, reputation, threat
from .models import IPRule, SecurityEvent, SecuritySetting
from .serializers import (
    IPRuleSerializer,
    KillSwitchSerializer,
    SecurityEventSerializer,
    SecuritySettingSerializer,
)

logger = logging.getLogger("apps.security")


def _int(request, name, default, lo, hi):
    try:
        return max(lo, min(hi, int(request.query_params.get(name, default))))
    except (TypeError, ValueError):
        return default


class SecuritySummaryView(APIView):
    """Threat summary + current posture for the dashboard landing panel."""

    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        window = _int(request, "window_hours", 24, 1, 720)
        config = conf.get_config()
        data = threat.summary(window_hours=window)
        data["posture"] = {
            "enabled": config.enabled,
            "mode": config.get("mode"),
            "fail_strategy": config.get("fail_strategy"),
            "waf_mode": config.get("waf.mode"),
            "bots_mode": config.get("bots.mode"),
            "kill": {
                "rate_limiter": bool(config.get("kill.rate_limiter")),
                "auth": bool(config.get("kill.auth")),
            },
            "config_generation": config.generation,
        }
        data["timeseries"] = threat.timeseries(window_hours=window)
        return Response(data)


class SecurityEventListView(APIView):
    """Paginated, filterable feed of the immutable security event trail."""

    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        limit = _int(request, "limit", 50, 1, 500)
        offset = _int(request, "offset", 0, 0, 1_000_000)
        qs = SecurityEvent.objects.all().order_by("-created_at")
        for field in ("event_type", "action", "ip"):
            value = request.query_params.get(field)
            if value:
                qs = qs.filter(**{field: value})
        total = qs.count()
        rows = qs[offset:offset + limit]
        return Response({
            "count": total,
            "results": SecurityEventSerializer(rows, many=True).data,
        })


class TopOffendersView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        window = _int(request, "window_hours", 24, 1, 720)
        return Response({"offenders": threat.top_offenders(window_hours=window)})


class IPRuleViewSet(viewsets.ModelViewSet):
    """Manage allow/deny/trust IP rules (dynamic rule editor). Hot-reloaded."""

    permission_classes = [IsPlatformAdmin]
    serializer_class = IPRuleSerializer
    queryset = IPRule.objects.all().order_by("-created_at")

    def perform_create(self, serializer):
        obj = serializer.save(created_by=self.request.user)
        record_event(self.request, action=AuditEvent.Action.CREATE,
                     message=f"Security IP rule created: {obj.action} {obj.cidr}",
                     meta={"cidr": obj.cidr, "rule_action": obj.action})

    def perform_destroy(self, instance):
        record_event(self.request, action=AuditEvent.Action.DELETE,
                     message=f"Security IP rule removed: {instance.action} {instance.cidr}",
                     meta={"cidr": instance.cidr})
        instance.delete()


class SecuritySettingViewSet(viewsets.ModelViewSet):
    """Runtime config rule editor (SecuritySetting rows). Every write hot-
    reloads the resolved config across all containers via the generation bump."""

    permission_classes = [IsPlatformAdmin]
    serializer_class = SecuritySettingSerializer
    queryset = SecuritySetting.objects.all().order_by("key")

    def perform_create(self, serializer):
        obj = serializer.save(updated_by=self.request.user)
        self._audit("created", obj)

    def perform_update(self, serializer):
        obj = serializer.save(updated_by=self.request.user)
        self._audit("updated", obj)

    def perform_destroy(self, instance):
        self._audit("removed", instance)
        instance.delete()

    def _audit(self, verb, obj):
        record_event(self.request, action=AuditEvent.Action.UPDATE,
                     message=f"Security setting {verb}: {obj.key}",
                     meta={"key": obj.key, "value": obj.value})


class ResolvedConfigView(APIView):
    """The fully-resolved live config snapshot (read-only) — so an operator can
    see exactly what every layer would apply right now, across all sources."""

    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        config = conf.get_config()
        return Response({"generation": config.generation, "config": config.data})


class ReputationClearView(APIView):
    permission_classes = [IsPlatformAdmin]

    def post(self, request):
        ip = (request.data.get("ip") or "").strip()
        if not ip:
            return Response({"detail": "ip is required."},
                            status=status.HTTP_400_BAD_REQUEST)
        reputation.clear(ip)
        record_event(request, action=AuditEvent.Action.UPDATE,
                     message=f"IP reputation cleared: {ip}", meta={"ip": ip})
        return Response({"detail": f"Reputation cleared for {ip}."})


class SecurityReportView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        period = request.query_params.get("period", "daily")
        if period not in ("daily", "weekly", "monthly"):
            period = "daily"
        data = reports.build(period=period)
        # NB: not "format" — that key is reserved by DRF's format-suffix machinery.
        if request.query_params.get("fmt") == "csv":
            resp = Response(reports.to_csv(data), content_type="text/csv")
            resp["Content-Disposition"] = f'attachment; filename="security-{period}.csv"'
            return resp
        return Response(data)


class KillSwitchView(APIView):
    """Emergency kill switch. Disables a security subsystem or engages
    maintenance/emergency DR mode — immediately, hot-reloaded, audited."""

    permission_classes = [IsPlatformAdmin]

    # security-config kill targets -> (setting key, value when engaged)
    _CONFIG_TARGETS = {
        "rate_limiter": ("kill.rate_limiter", True, True),   # engage-value, disengage=delete
        "auth": ("kill.auth", True, True),
        "waf": ("waf.enabled", False, False),                # engage disables; disengage restores True
        "bots": ("bots.enabled", False, False),
    }

    def post(self, request):
        serializer = KillSwitchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target = serializer.validated_data["target"]
        engage = serializer.validated_data["engage"]
        reason = serializer.validated_data.get("reason", "")

        if target in ("maintenance", "emergency"):
            detail = self._dr_mode(target, engage, reason, request)
        else:
            detail = self._config_kill(target, engage)

        record_event(request, action=AuditEvent.Action.UPDATE,
                     message=f"Kill switch: {target} {'engaged' if engage else 'restored'}",
                     meta={"target": target, "engage": engage, "reason": reason})
        logger.warning("KILL SWITCH %s %s by user=%s reason=%s",
                       target, "ENGAGE" if engage else "RESTORE",
                       getattr(request.user, "pk", None), reason)
        return Response({"detail": detail, "target": target, "engaged": engage})

    def _config_kill(self, target, engage):
        key, engage_value, delete_on_restore = self._CONFIG_TARGETS[target]
        if not engage and delete_on_restore:
            SecuritySetting.objects.filter(key=key).delete()
            return f"{target} restored (kill removed)."
        value = engage_value if engage else True   # waf/bots restore -> enabled True
        SecuritySetting.objects.update_or_create(
            key=key, defaults={"value": value, "active": True,
                               "note": "kill switch"}
        )
        return f"{target} {'disabled' if engage else 'restored'}."

    def _dr_mode(self, target, engage, reason, request):
        try:
            from apps.backups.dr import set_mode

            mode = target if engage else "normal"
            set_mode(mode, reason=reason or f"kill switch: {target}",
                     user=request.user, request=request)
            return f"DR mode set to {mode}."
        except Exception as exc:
            logger.error("kill switch DR mode change failed: %s", exc, exc_info=True)
            return f"Could not change DR mode: {exc}"
