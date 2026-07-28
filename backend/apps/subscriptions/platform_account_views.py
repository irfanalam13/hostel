"""Super-Admin account directory — every user account across every tenant and
the plan/hostel it's currently attached to. Answers "who is this account and
what are they paying for" without having to cross-reference the hostels
overview and subscriptions views by hand.
"""
from django.db.models import Prefetch, Q
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User, UserHostel

from .permissions import IsPlatformAdmin
from .platform_views import PLATFORM_TAGS


def _membership_row(link):
    h = link.hostel
    return {
        "hostel_id": str(h.pk),
        "hostel_name": h.name,
        "hostel_code": h.code,
        "hostel_status": h.status,
        "plan_id": str(h.plan_id) if h.plan_id else None,
        "plan_name": h.plan.name if h.plan_id else (h.plan_name or None),
        "subscription_active_until": h.subscription_active_until,
    }


def _account_row(user):
    return {
        "id": str(user.pk),
        "username": user.username,
        "email": user.email,
        "full_name": f"{user.first_name} {user.last_name}".strip(),
        "role": user.role,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "last_login": user.last_login,
        "date_joined": user.date_joined,
        "memberships": [_membership_row(link) for link in user.hostel_links.all()],
    }


@extend_schema(tags=PLATFORM_TAGS)
class PlatformAccountsView(APIView):
    """Read-only: every non-consumer account plus which hostel(s)/plan(s) it's
    linked to. Account volume grows with tenant count (unlike the bounded
    config lists elsewhere in this app), so this paginates via limit/offset
    rather than returning everything.
    """

    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        qs = (
            User.objects.exclude(role="CONSUMER")
            .prefetch_related(
                Prefetch(
                    "hostel_links",
                    queryset=UserHostel.objects.filter(
                        is_active=True, hostel__is_platform_workspace=False
                    ).select_related("hostel__plan"),
                )
            )
            .order_by("username")
        )

        search = request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(username__icontains=search)
                | Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )

        role = request.query_params.get("role")
        if role:
            qs = qs.filter(role=role)

        plan_id = request.query_params.get("plan")
        if plan_id:
            qs = qs.filter(hostel_links__hostel__plan_id=plan_id).distinct()

        total = qs.count()
        try:
            limit = int(request.query_params.get("limit", 50))
            offset = int(request.query_params.get("offset", 0))
        except ValueError:
            limit, offset = 50, 0
        page = qs[offset : offset + limit]

        # Deliberately not {count, next, previous, results} — that exact key
        # set makes StandardJSONRenderer flatten "results" into the envelope's
        # `data` and drop `count` into `meta.pagination`, which apiFetch()
        # discards. Naming it `accounts` keeps the total reachable by callers.
        return Response(
            {"count": total, "accounts": [_account_row(u) for u in page]}
        )
