from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import STAFF_ROLES, HasHostelContext

from .models import (
    Notification,
    NotificationRecipient,
    PushSubscription,
)
from .serializers import (
    InboxNotificationSerializer,
    NotificationAdminSerializer,
    NotificationCreateSerializer,
    PushSubscribeSerializer,
    PushUnsubscribeSerializer,
)
from .services import create_notification


def _is_staff(user) -> bool:
    return getattr(user, "is_superuser", False) or getattr(user, "role", None) in STAFF_ROLES


# --------------------------------------------------------------------------- #
# Push subscription endpoints (consumed by src/shared/pwa/push.ts)
# --------------------------------------------------------------------------- #
class PushSubscribeView(APIView):
    permission_classes = [IsAuthenticated, HasHostelContext]

    def post(self, request):
        serializer = PushSubscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sub = serializer.validated_data["subscription"]
        keys = sub["keys"]

        obj, created = PushSubscription.objects.update_or_create(
            endpoint=sub["endpoint"],
            defaults={
                "user": request.user,
                "hostel": getattr(request, "hostel", None),
                "p256dh": keys["p256dh"],
                "auth": keys["auth"],
                "user_agent": serializer.validated_data.get("user_agent", "")[:300],
                "is_active": True,
                "failure_count": 0,
                "last_used_at": timezone.now(),
            },
        )
        return Response(
            {"id": str(obj.id), "created": created},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class PushUnsubscribeView(APIView):
    permission_classes = [IsAuthenticated, HasHostelContext]

    def post(self, request):
        serializer = PushUnsubscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Only the owner may remove their own subscription.
        deleted, _ = PushSubscription.objects.filter(
            endpoint=serializer.validated_data["endpoint"], user=request.user
        ).delete()
        return Response({"removed": bool(deleted)}, status=status.HTTP_200_OK)


# --------------------------------------------------------------------------- #
# Notifications: inbox (read state) + staff send/history
# --------------------------------------------------------------------------- #
class NotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """The current user's notification inbox, scoped to the active hostel."""

    serializer_class = InboxNotificationSerializer
    permission_classes = [IsAuthenticated, HasHostelContext]

    def get_queryset(self):
        qs = (
            NotificationRecipient.objects.select_related("notification")
            .filter(user=self.request.user, notification__hostel=self.request.hostel)
        )
        is_read = self.request.query_params.get("is_read")
        if is_read in ("true", "false"):
            qs = qs.filter(is_read=(is_read == "true"))
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(notification__category=category)
        return qs

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        count = self.get_queryset().filter(is_read=False).count()
        return Response({"unread": count})

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        rec = self.get_queryset().filter(pk=pk).first()
        if not rec:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        was_unread = not rec.is_read
        rec.mark_read()
        if was_unread:
            Notification.objects.filter(pk=rec.notification_id).update(
                read_count=NotificationRecipient.objects.filter(
                    notification_id=rec.notification_id, is_read=True
                ).count()
            )
        return Response({"id": str(rec.id), "is_read": True})

    @action(detail=False, methods=["post"])
    def read_all(self, request):
        unread = self.get_queryset().filter(is_read=False)
        ids = list(unread.values_list("notification_id", flat=True))
        n = unread.update(is_read=True, read_at=timezone.now())
        for nid in set(ids):
            Notification.objects.filter(pk=nid).update(
                read_count=NotificationRecipient.objects.filter(
                    notification_id=nid, is_read=True
                ).count()
            )
        return Response({"marked_read": n})

    @action(detail=False, methods=["post"])
    def send(self, request):
        """Staff-only: create and dispatch (or schedule) a notification."""
        if not _is_staff(request.user):
            return Response({"detail": "Staff only."}, status=status.HTTP_403_FORBIDDEN)
        serializer = NotificationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        notification = create_notification(
            hostel=request.hostel,
            created_by=request.user,
            title=data["title"],
            body=data.get("body", ""),
            category=data["category"],
            priority=data["priority"],
            url=data.get("url", "/dashboard"),
            icon=data.get("icon", ""),
            tag=data.get("tag", ""),
            data=data.get("data", {}),
            audience=data["audience"],
            target_roles=data.get("target_roles", []),
            user_ids=data.get("user_ids", []),
            scheduled_at=data.get("scheduled_at"),
        )
        return Response(
            NotificationAdminSerializer(notification).data, status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=["get"])
    def sent(self, request):
        """Staff-only: notifications created in this hostel, with delivery stats."""
        if not _is_staff(request.user):
            return Response({"detail": "Staff only."}, status=status.HTTP_403_FORBIDDEN)
        qs = Notification.objects.filter(hostel=request.hostel).select_related("created_by")
        category = request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)
        page = self.paginate_queryset(qs)
        serializer = NotificationAdminSerializer(page if page is not None else qs, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)
