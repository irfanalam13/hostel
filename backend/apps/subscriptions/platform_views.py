"""Super-Admin platform API (Modules 2, 3, 5-8, 15, 17-20).

Everything here is gated by :class:`IsPlatformAdmin` (Django ``is_superuser``),
supports search/filter/ordering, and audit-logs every mutation. Mounted under
``/api/platform/``.
"""
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auditlog.models import AuditEvent
from apps.auditlog.services import record_event
from apps.tenants.models import Hostel, Plan

from . import lifecycle, services
from .models import (
    Feature,
    FeatureCategory,
    FeatureDependency,
    FeatureOverride,
    LimitDefinition,
    LimitOverride,
    SubscriptionEvent,
)
from .permissions import IsPlatformAdmin
from .platform_serializers import (
    FeatureCategorySerializer,
    FeatureDependencySerializer,
    FeatureOverrideSerializer,
    FeatureSerializer,
    LimitDefinitionSerializer,
    LimitOverrideSerializer,
    PlatformPlanSerializer,
    SubscriptionEventSerializer,
)

PLATFORM_TAGS = ["Platform / Subscriptions"]


class PlatformViewSet(viewsets.ModelViewSet):
    """Base: super-admin only, filterable, audited."""

    permission_classes = [IsPlatformAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    # The platform config lists are bounded (dozens of rows) and the UI needs
    # them whole (feature matrix, comparison) — return full lists, not pages.
    pagination_class = None
    audit_entity = "object"

    def _audit(self, verb, obj, message="", meta=None, hostel=None):
        record_event(
            self.request,
            action=verb,
            entity_type=self.audit_entity,
            entity_id=getattr(obj, "pk", ""),
            message=message[:255],
            meta=meta or {},
            hostel=hostel,
        )

    def perform_create(self, serializer):
        obj = serializer.save()
        self._audit(AuditEvent.Action.CREATE, obj, f"{self.audit_entity} created: {obj}")

    def perform_update(self, serializer):
        obj = serializer.save()
        self._audit(AuditEvent.Action.UPDATE, obj, f"{self.audit_entity} updated: {obj}")

    def perform_destroy(self, instance):
        self._audit(AuditEvent.Action.DELETE, instance, f"{self.audit_entity} deleted: {instance}")
        instance.delete()


# --------------------------------------------------------------------------- #
# Catalog CRUD (Module 1)
# --------------------------------------------------------------------------- #
@extend_schema(tags=PLATFORM_TAGS)
class FeatureCategoryViewSet(PlatformViewSet):
    queryset = FeatureCategory.objects.all()
    serializer_class = FeatureCategorySerializer
    audit_entity = "feature_category"
    search_fields = ["name", "key", "description"]
    filterset_fields = ["is_active"]
    ordering_fields = ["sort_order", "name", "created_at"]


@extend_schema(tags=PLATFORM_TAGS)
class FeatureViewSet(PlatformViewSet):
    queryset = (
        Feature.objects.select_related("category")
        .prefetch_related("dependency_links__requires")
        .all()
    )
    serializer_class = FeatureSerializer
    audit_entity = "feature"
    search_fields = ["name", "display_name", "key", "description"]
    filterset_fields = ["category", "release_stage", "is_active", "is_enterprise_only", "is_beta"]
    ordering_fields = ["sort_order", "name", "created_at"]

    def perform_create(self, serializer):
        obj = serializer.save(created_by=self.request.user, updated_by=self.request.user)
        self._audit(AuditEvent.Action.CREATE, obj, f"feature created: {obj}")

    def perform_update(self, serializer):
        obj = serializer.save(updated_by=self.request.user)
        self._audit(AuditEvent.Action.UPDATE, obj, f"feature updated: {obj}")


@extend_schema(tags=PLATFORM_TAGS)
class LimitDefinitionViewSet(PlatformViewSet):
    queryset = LimitDefinition.objects.select_related("category").all()
    serializer_class = LimitDefinitionSerializer
    audit_entity = "limit_definition"
    search_fields = ["name", "key", "description"]
    filterset_fields = ["category", "is_active", "allow_unlimited"]
    ordering_fields = ["sort_order", "name", "created_at"]


@extend_schema(tags=PLATFORM_TAGS)
class FeatureDependencyViewSet(PlatformViewSet):
    queryset = FeatureDependency.objects.select_related("feature", "requires").all()
    serializer_class = FeatureDependencySerializer
    audit_entity = "feature_dependency"
    search_fields = ["feature__key", "requires__key"]
    filterset_fields = ["feature", "requires"]


# --------------------------------------------------------------------------- #
# Overrides (Modules 13 & 14)
# --------------------------------------------------------------------------- #
@extend_schema(tags=PLATFORM_TAGS)
class FeatureOverrideViewSet(PlatformViewSet):
    queryset = FeatureOverride.objects.select_related("hostel", "feature").all()
    serializer_class = FeatureOverrideSerializer
    audit_entity = "feature_override"
    search_fields = ["hostel__name", "hostel__code", "feature__key", "reason"]
    filterset_fields = ["hostel", "feature", "is_enabled"]

    def perform_create(self, serializer):
        obj = serializer.save(created_by=self.request.user)
        self._audit(
            AuditEvent.Action.CREATE, obj,
            f"feature override: {obj.feature.key}={'grant' if obj.is_enabled else 'revoke'}",
            meta={"feature": obj.feature.key, "is_enabled": obj.is_enabled},
            hostel=obj.hostel,
        )

    def perform_update(self, serializer):
        obj = serializer.save()
        self._audit(AuditEvent.Action.UPDATE, obj, f"feature override updated: {obj.feature.key}",
                    hostel=obj.hostel)


@extend_schema(tags=PLATFORM_TAGS)
class LimitOverrideViewSet(PlatformViewSet):
    queryset = LimitOverride.objects.select_related("hostel", "limit").all()
    serializer_class = LimitOverrideSerializer
    audit_entity = "limit_override"
    search_fields = ["hostel__name", "hostel__code", "limit__key", "reason"]
    filterset_fields = ["hostel", "limit", "is_unlimited"]

    def perform_create(self, serializer):
        obj = serializer.save(created_by=self.request.user)
        self._audit(AuditEvent.Action.CREATE, obj, f"limit override: {obj.limit.key}",
                    meta={"limit": obj.limit.key, "value": obj.value, "is_unlimited": obj.is_unlimited},
                    hostel=obj.hostel)

    def perform_update(self, serializer):
        obj = serializer.save()
        self._audit(AuditEvent.Action.UPDATE, obj, f"limit override updated: {obj.limit.key}",
                    hostel=obj.hostel)


# --------------------------------------------------------------------------- #
# Plans (Modules 2, 5, 6, 7)
# --------------------------------------------------------------------------- #
def _feature_rows(plan):
    """Feature list with per-plan enabled state + dependency info."""
    fmap = services.plan_feature_map(plan)
    rows = []
    for f in (
        Feature.objects.filter(is_active=True)
        .select_related("category")
        .prefetch_related("dependency_links__requires")
    ):
        rows.append(
            {
                "feature": str(f.id),
                "key": f.key,
                "name": f.label,
                "category_key": f.category.key,
                "category_name": f.category.name,
                "release_stage": f.release_stage,
                "is_enterprise_only": f.is_enterprise_only,
                "is_beta": f.is_beta,
                "enabled": fmap.get(f.key, False),
                "requires": [d.requires.key for d in f.dependency_links.all()],
            }
        )
    return rows


def _limit_rows(plan):
    lmap = services.plan_limit_map(plan)
    rows = []
    for ld in LimitDefinition.objects.filter(is_active=True).select_related("category"):
        val = lmap.get(ld.key, ld.default_value)
        rows.append(
            {
                "limit": str(ld.id),
                "key": ld.key,
                "name": ld.name,
                "unit": ld.unit,
                "allow_unlimited": ld.allow_unlimited,
                "value": val,                 # None == unlimited
                "is_unlimited": val is None,
                "default_value": ld.default_value,
            }
        )
    return rows


@extend_schema(tags=PLATFORM_TAGS)
class PlanViewSet(PlatformViewSet):
    queryset = Plan.objects.all().prefetch_related("plan_features", "plan_limits")
    serializer_class = PlatformPlanSerializer
    audit_entity = "plan"
    search_fields = ["name", "slug", "description"]
    filterset_fields = [
        "visibility", "is_active", "is_archived", "is_featured",
        "is_recommended", "billing_interval",
    ]
    ordering_fields = ["sort_order", "price_monthly", "name", "created_at"]

    # ---- lifecycle actions (Module 2) ---------------------------------- #
    def _set_flags(self, request, pk, message, **flags):
        plan = self.get_object()
        for field, val in flags.items():
            setattr(plan, field, val)
        plan.save(update_fields=list(flags.keys()) + ["updated_at"])
        self._audit(AuditEvent.Action.UPDATE, plan, message, meta=flags)
        return Response(self.get_serializer(plan).data)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        return self._set_flags(request, pk, "plan archived", is_archived=True, is_active=False)

    @action(detail=True, methods=["post"])
    def unarchive(self, request, pk=None):
        return self._set_flags(request, pk, "plan unarchived", is_archived=False)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        return self._set_flags(request, pk, "plan activated", is_active=True, is_archived=False)

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        return self._set_flags(request, pk, "plan deactivated", is_active=False)

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        plan = self.get_object()
        clone = services.duplicate_plan(
            plan, new_name=request.data.get("name", ""), created_by=request.user
        )
        self._audit(AuditEvent.Action.CREATE, clone, f"plan duplicated from {plan.name}",
                    meta={"source": str(plan.pk)})
        return Response(self.get_serializer(clone).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def reorder(self, request):
        """Body: ``[{"id": "..", "sort_order": 0}, ...]``."""
        items = request.data if isinstance(request.data, list) else request.data.get("items", [])
        updated = 0
        for item in items:
            n = Plan.objects.filter(pk=item.get("id")).update(sort_order=item.get("sort_order", 0))
            updated += n
        self._audit(AuditEvent.Action.UPDATE, Plan(), "plans reordered", meta={"count": updated})
        return Response({"updated": updated})

    @action(detail=False, methods=["post"])
    def bulk(self, request):
        """Body: ``{"ids": [...], "action": "activate|deactivate|archive|unarchive|delete"}``."""
        ids = request.data.get("ids", [])
        act = request.data.get("action", "")
        qs = Plan.objects.filter(pk__in=ids)
        mapping = {
            "activate": {"is_active": True, "is_archived": False},
            "deactivate": {"is_active": False},
            "archive": {"is_archived": True, "is_active": False},
            "unarchive": {"is_archived": False},
        }
        if act == "delete":
            count = qs.count()
            qs.delete()
        elif act in mapping:
            count = qs.update(**mapping[act])
        else:
            return Response({"detail": "Unknown bulk action."}, status=400)
        self._audit(AuditEvent.Action.UPDATE, Plan(), f"bulk {act}", meta={"ids": list(map(str, ids)), "count": count})
        return Response({"action": act, "count": count})

    # ---- feature-access manager (Module 3) ----------------------------- #
    @action(detail=True, methods=["get", "put"], url_path="features")
    def features_manager(self, request, pk=None):
        plan = self.get_object()
        if request.method == "GET":
            return Response(_feature_rows(plan))

        payload = request.data.get("features", request.data)
        if not isinstance(payload, dict):
            return Response({"detail": "Expected a {feature_key: bool} map."}, status=400)
        force = str(request.data.get("force", request.query_params.get("force", ""))).lower() in (
            "1", "true", "yes",
        )
        try:
            services.set_plan_features(plan, payload, force=force)
        except services.DependencyError as e:
            return Response(
                {"code": "dependency_violation", "detail": "Enable required features first, or pass force=true.",
                 "violations": e.violations},
                status=status.HTTP_400_BAD_REQUEST,
            )
        self._audit(AuditEvent.Action.UPDATE, plan, "plan features updated",
                    meta={"changed": list(payload.keys()), "forced": force})
        return Response(_feature_rows(plan))

    # ---- limits manager (Module 4) ------------------------------------- #
    @action(detail=True, methods=["get", "put"], url_path="limits")
    def limits_manager(self, request, pk=None):
        plan = self.get_object()
        if request.method == "GET":
            return Response(_limit_rows(plan))

        payload = request.data.get("limits", request.data)
        if not isinstance(payload, dict):
            return Response({"detail": "Expected a {limit_key: {value, is_unlimited}} map."}, status=400)
        services.set_plan_limits(plan, payload)
        self._audit(AuditEvent.Action.UPDATE, plan, "plan limits updated",
                    meta={"changed": list(payload.keys())})
        return Response(_limit_rows(plan))

    # ---- comparison matrix (Module 6) ---------------------------------- #
    @action(detail=False, methods=["get"])
    def comparison(self, request):
        include_all = str(request.query_params.get("include_all", "")).lower() in ("1", "true", "yes")
        plans_qs = Plan.objects.all() if include_all else Plan.objects.filter(is_archived=False)
        plans = list(plans_qs.order_by("sort_order", "price_monthly", "name"))

        fmaps = {p.pk: services.plan_feature_map(p) for p in plans}
        lmaps = {p.pk: services.plan_limit_map(p) for p in plans}

        features = [
            {
                "key": f.key,
                "name": f.label,
                "category_key": f.category.key,
                "category_name": f.category.name,
                "values": {str(p.pk): fmaps[p.pk].get(f.key, False) for p in plans},
            }
            for f in Feature.objects.filter(is_active=True).select_related("category")
        ]
        limits = [
            {
                "key": ld.key,
                "name": ld.name,
                "unit": ld.unit,
                "values": {str(p.pk): lmaps[p.pk].get(ld.key, ld.default_value) for p in plans},
            }
            for ld in LimitDefinition.objects.filter(is_active=True)
        ]
        return Response(
            {
                "plans": [
                    {
                        "id": str(p.pk), "name": p.name, "slug": p.slug,
                        "price_monthly": str(p.price_monthly), "billing_interval": p.billing_interval,
                        "is_recommended": p.is_recommended, "is_featured": p.is_featured,
                        "badge": p.badge,
                    }
                    for p in plans
                ],
                "features": features,
                "limits": limits,
            }
        )

    # ---- import / export (Module 18) ----------------------------------- #
    @action(detail=False, methods=["get"])
    def export(self, request):
        self._audit(AuditEvent.Action.EXPORT, Plan(), "plans exported")
        return Response({"plans": services.export_plans()})

    @action(detail=False, methods=["post"], url_path="import")
    def import_plans(self, request):
        rows = request.data.get("plans") if isinstance(request.data, dict) else request.data
        if not isinstance(rows, list):
            return Response({"detail": "Expected a list of plans (or {plans: [...]})."}, status=400)
        result = services.import_plans(rows, created_by=request.user)
        self._audit(AuditEvent.Action.CREATE, Plan(), "plans imported", meta=result)
        return Response(result)


# --------------------------------------------------------------------------- #
# Subscription lifecycle & analytics (Modules 9 & 16)
# --------------------------------------------------------------------------- #
def _hostel_subscription_row(h):
    return {
        "id": str(h.pk),
        "name": h.name,
        "code": h.code,
        "status": h.status,
        "plan": str(h.plan_id) if h.plan_id else None,
        "plan_name": h.plan.name if h.plan_id else (h.plan_name or None),
        "mrr": str(lifecycle.monthly_equivalent(h.plan)) if h.plan_id else "0",
        "trial_ends_at": h.trial_ends_at,
        "subscription_active_until": h.subscription_active_until,
    }


@extend_schema(tags=PLATFORM_TAGS)
class PlatformSubscriptionsView(APIView):
    """GET list of hostels + their plan/status; POST assigns a plan."""

    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        qs = Hostel.objects.filter(is_deleted=False).select_related("plan").order_by("name")
        search = request.query_params.get("search")
        if search:
            qs = qs.filter(name__icontains=search)
        return Response([_hostel_subscription_row(h) for h in qs])

    def post(self, request):
        hostel = get_object_or_404(Hostel, pk=request.data.get("hostel"))
        plan = get_object_or_404(Plan, pk=request.data.get("plan"))
        event = lifecycle.assign_plan(
            hostel,
            plan,
            actor=request.user,
            reason=request.data.get("reason", ""),
            status=request.data.get("status", "active"),
        )
        record_event(
            request,
            action=AuditEvent.Action.UPDATE,
            entity_type="subscription",
            entity_id=str(hostel.pk),
            message=f"{event.kind} → {plan.name}",
            meta={"kind": event.kind, "plan": str(plan.pk)},
            hostel=hostel,
        )
        return Response(_hostel_subscription_row(hostel), status=status.HTTP_200_OK)


@extend_schema(tags=PLATFORM_TAGS)
class SubscriptionHistoryView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request, hostel_id):
        events = SubscriptionEvent.objects.filter(hostel_id=hostel_id).select_related(
            "from_plan", "to_plan", "actor"
        )
        return Response(SubscriptionEventSerializer(events, many=True).data)


@extend_schema(tags=PLATFORM_TAGS)
class AnalyticsView(APIView):
    """Platform KPIs: MRR/ARR, hostel & plan counts, distribution, adoption."""

    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        return Response(lifecycle.analytics())
