"""Authenticated status feed consumed by every zone's frontend.

Returns the banners/announcements the current user should see, any active or
imminent maintenance, currently-open public incidents, and the fully-resolved
feature-flag set for the caller's tenant+role. Read-only, cheap, cacheable.
"""
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import flags
from .models import Announcement, Audience, Incident, MaintenanceWindow
from .serializers import (
    AnnouncementSerializer,
    IncidentSerializer,
    MaintenanceWindowSerializer,
)

# Which audiences a user in a given role bucket is allowed to see.
_ADMIN_ROLES = {"OWNER", "ADMIN"}
_STAFF_ROLES = {"OWNER", "ADMIN", "MANAGER", "RECEPTIONIST", "STAFF", "ACCOUNTANT", "WARDEN"}


def _visible_audiences(user) -> set:
    role = getattr(user, "role", None)
    audiences = {Audience.ALL}
    if getattr(user, "is_superuser", False) or role in _ADMIN_ROLES:
        audiences |= {Audience.STAFF, Audience.ADMINS}
    elif role in _STAFF_ROLES:
        audiences.add(Audience.STAFF)
    return audiences


class OpsStatusView(APIView):
    """The single call the frontend makes on load / poll to render ops state."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        user = request.user
        hostel = getattr(request, "hostel", None)

        announcements = [
            a for a in Announcement.objects.filter(is_active=True,
                                                    audience__in=_visible_audiences(user))
            if a.live
        ]

        upcoming = MaintenanceWindow.objects.filter(
            status__in=[MaintenanceWindow.Status.SCHEDULED,
                        MaintenanceWindow.Status.IN_PROGRESS],
            scheduled_end__gte=now,
        )[:10]

        incidents = Incident.objects.filter(is_public=True).exclude(
            status=Incident.Status.RESOLVED
        )[:10]

        return Response({
            "announcements": AnnouncementSerializer(announcements, many=True).data,
            "maintenance": MaintenanceWindowSerializer(upcoming, many=True).data,
            "incidents": IncidentSerializer(incidents, many=True).data,
            "flags": flags.evaluate_all(hostel=hostel, user=user),
            "server_time": now.isoformat(),
        })
