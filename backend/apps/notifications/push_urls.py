"""Web Push subscription endpoints, mounted at /api/push/.

Matches the frontend contract in src/shared/pwa/push.ts:
    POST /api/push/subscribe/
    POST /api/push/unsubscribe/
"""
from django.urls import path

from .views import PushSubscribeView, PushUnsubscribeView

urlpatterns = [
    path("subscribe/", PushSubscribeView.as_view(), name="push-subscribe"),
    path("unsubscribe/", PushUnsubscribeView.as_view(), name="push-unsubscribe"),
]
