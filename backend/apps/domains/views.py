"""Custom-domain management API (Prompt 05).

All endpoints operate on ``request.hostel`` — isolation inherited from the
workspace-bound auth stack. Reads need ``workspace.view``; every mutation
needs ``workspace.manage`` and is audited; verification is throttled (each
attempt performs live DNS lookups).
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.rbac import RequirePermission

from . import services
from .models import CustomDomain

CanView = RequirePermission("workspace.view")
CanManage = RequirePermission("workspace.manage")


def _serialize(record: CustomDomain) -> dict:
    return {
        "id": str(record.id),
        "domain": record.domain,
        "status": record.status,
        "is_primary": record.is_primary,
        "verification_method": record.verification_method,
        "verified_at": record.verified_at,
        "last_checked_at": record.last_checked_at,
        "last_error": record.last_error,
        "ssl_status": record.ssl_status,
        "ssl_expires_at": record.ssl_expires_at,
        "dns_health": record.dns_health,
        "records": {"txt": record.txt_record, "cname": record.cname_record},
        "url": f"https://{record.domain}",
        "created_at": record.created_at,
    }


def _get_record(request, domain_id) -> CustomDomain:
    record = CustomDomain.objects.filter(id=domain_id, hostel=request.hostel).first()
    if record is None:
        raise ValidationError({"detail": "Domain not found in this workspace."}, code="not_found")
    return record


def _raise_drf(exc: DjangoValidationError):
    raise ValidationError(getattr(exc, "message_dict", None) or list(exc.messages))


class DomainListView(APIView):
    permission_classes = [IsAuthenticated, CanView]

    def get(self, request):
        records = CustomDomain.objects.filter(hostel=request.hostel)
        return Response({
            "workspace_url": request.hostel.workspace_url,
            "public_url": services.public_url_for(request.hostel),
            "limit": services.domain_limit_for(request.hostel),
            "domains": [_serialize(r) for r in records],
        })

    def post(self, request):
        if not CanManage().has_permission(request, self):
            return Response({"detail": "You do not have permission to manage domains."},
                            status=status.HTTP_403_FORBIDDEN)
        try:
            record = services.add_domain(
                request.hostel, str(request.data.get("domain") or ""), actor=request.user
            )
        except DjangoValidationError as exc:
            _raise_drf(exc)
        return Response(_serialize(record), status=status.HTTP_201_CREATED)


class DomainVerifyView(APIView):
    permission_classes = [IsAuthenticated, CanManage]
    throttle_scope = "domain_verify"

    def post(self, request, domain_id):
        record = services.verify_domain(_get_record(request, domain_id), actor=request.user)
        return Response(_serialize(record))


class DomainActivateView(APIView):
    permission_classes = [IsAuthenticated, CanManage]

    def post(self, request, domain_id):
        make_primary = bool(request.data.get("make_primary", True))
        try:
            record = services.activate_domain(
                _get_record(request, domain_id), actor=request.user, make_primary=make_primary
            )
        except DjangoValidationError as exc:
            _raise_drf(exc)
        return Response(_serialize(record))


class DomainPrimaryView(APIView):
    permission_classes = [IsAuthenticated, CanManage]

    def post(self, request, domain_id):
        try:
            record = services.set_primary_domain(_get_record(request, domain_id), actor=request.user)
        except DjangoValidationError as exc:
            _raise_drf(exc)
        return Response(_serialize(record))


class DomainDisableView(APIView):
    permission_classes = [IsAuthenticated, CanManage]

    def post(self, request, domain_id):
        record = services.disable_domain(_get_record(request, domain_id), actor=request.user)
        return Response(_serialize(record))


class DomainSslView(APIView):
    permission_classes = [IsAuthenticated, CanView]
    throttle_scope = "domain_verify"

    def post(self, request, domain_id):
        record = services.check_ssl(_get_record(request, domain_id))
        return Response(_serialize(record))


class DomainDeleteView(APIView):
    permission_classes = [IsAuthenticated, CanManage]

    def delete(self, request, domain_id):
        services.remove_domain(_get_record(request, domain_id), actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
