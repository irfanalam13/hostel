from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AiConfigView,
    AiDashboardView,
    ChatSessionView,
    ConversationCompleteView,
    ConversationContextView,
    ConversationViewSet,
    ToolListView,
    ToolRunView,
)

router = DefaultRouter()
router.register(r"conversations", ConversationViewSet, basename="ai-conversations")

urlpatterns = [
    # Browser-facing (session cookie)
    path("chat/", ChatSessionView.as_view(), name="ai-chat"),
    path("config/", AiConfigView.as_view(), name="ai-config"),
    path("dashboard/", AiDashboardView.as_view(), name="ai-dashboard"),
    # Service-facing (Bearer context token) — called by the ML_hostel service
    path("conversations/<uuid:pk>/context/", ConversationContextView.as_view(), name="ai-conv-context"),
    path("conversations/<uuid:pk>/complete/", ConversationCompleteView.as_view(), name="ai-conv-complete"),
    path("tools/", ToolListView.as_view(), name="ai-tools"),
    path("tools/<str:name>/", ToolRunView.as_view(), name="ai-tool-run"),
]

urlpatterns += router.urls
