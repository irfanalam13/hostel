from django.utils.deprecation import MiddlewareMixin

from .models import TimeStampedModel
from django.db import models
from django.conf import settings

class AuditLog(TimeStampedModel):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    method = models.CharField(max_length=10, blank=True)
    path = models.CharField(max_length=255, blank=True)
    ip = models.CharField(max_length=64, blank=True)
    status_code = models.IntegerField(null=True, blank=True)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        app_label = "common"
        indexes = [models.Index(fields=["created_at", "actor"])]

class AuditLogMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        try:
            user = getattr(request, "user", None)
            ip = request.META.get("REMOTE_ADDR", "")
            meta = {"ua": request.META.get("HTTP_USER_AGENT", "")[:200]}

            # store minimal only
            AuditLog.objects.create(
                actor=user if getattr(user, "is_authenticated", False) else None,
                method=getattr(request, "method", ""),
                path=getattr(request, "path", "")[:255],
                ip=ip[:64],
                status_code=getattr(response, "status_code", None),
                meta=meta,
            )
        except Exception:
            # never break request because of audit
            pass
        return response