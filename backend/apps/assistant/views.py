"""AI assistant gateway (BFF).

Two audiences, two auth models:

* **Browser** (session cookie) — starts chat sessions, lists conversations,
  reads the AI dashboard. Gated by ``IsHostelResolved`` + ``ActionPermissions``
  (``ai.*``) + ``RequiresFeature("ai_chat")``, exactly like every other module.
* **ML_hostel service** (Bearer context token) — pulls conversation context,
  runs read-only tools, and writes back the completed answer. Gated by
  ``IsMlContext``; the tenant/user/permissions all come from the signed token.

No LLM logic lives here — this module only authorises, persists, and audits.
"""
from decimal import Decimal

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auditlog.models import AuditEvent
from apps.auditlog.services import record_event
from apps.common.permissions import IsHostelResolved
from apps.common.rbac import ActionPermissions, user_permissions
from apps.subscriptions.gates import RequiresFeature

from . import guardrails, metrics, tools
from .models import AiUsage, Conversation, Message
from .permissions import IsMlContext
from .serializers import ConversationDetailSerializer, ConversationSerializer
from .tokens import mint_context_token

CHAT_FEATURE = RequiresFeature("ai_chat")
CONTEXT_MESSAGE_LIMIT = 20


def _stream_base() -> str:
    """Browser-reachable base for the ML service SSE stream.

    Defaults to the same-origin ``/ai`` path (fronted by the gateway/proxy in
    dev and prod) so the browser never makes a cross-origin request; overridable
    per-deploy via ``ML_PUBLIC_URL`` when the service has its own hostname.
    """
    return (settings.ML_PUBLIC_URL or "/ai").rstrip("/")


def _check_quota(hostel):
    """Enforce the ``max_ai_requests`` monthly quota when entitlements are live."""
    if not getattr(settings, "ENTITLEMENTS_ENFORCED", False):
        return
    from apps.subscriptions.entitlements import Entitlements
    from apps.subscriptions.exceptions import PlanLimitExceeded

    limit = Entitlements(hostel).limit("max_ai_requests")
    if limit is None:
        return
    now = timezone.localdate()
    used = AiUsage.objects.filter(
        hostel=hostel, created_at__year=now.year, created_at__month=now.month
    ).count()
    if used >= limit:
        raise PlanLimitExceeded("max_ai_requests", "AI requests", used, limit)


# --------------------------------------------------------------------------- #
# Browser-facing (session cookie)
# --------------------------------------------------------------------------- #
class ChatSessionView(APIView):
    """Start (or continue) a chat turn.

    Persists the user's message, enforces quota/RBAC/plan, then mints a
    short-lived context token and hands back the SSE stream URL. The browser
    opens that stream against the ML service, which reads this conversation and
    streams the answer back.
    """

    permission_classes = [IsHostelResolved, ActionPermissions, CHAT_FEATURE]
    permission_map = {"post": ["ai.chat"]}

    def post(self, request):
        message = (request.data.get("message") or "").strip()
        if not message:
            raise ValidationError({"message": "This field is required."})

        hostel = request.hostel
        _check_quota(hostel)
        # AI/MLOps guardrails: input size cap + per-tenant daily cost budget.
        guardrails.enforce_pre_chat(message=message, hostel=hostel)

        conv_id = request.data.get("conversation_id")
        if conv_id:
            conv = get_object_or_404(
                Conversation, pk=conv_id, hostel=hostel, user=request.user
            )
        else:
            conv = Conversation.objects.create(
                hostel=hostel,
                user=request.user,
                title=message[:80],
            )

        Message.objects.create(conversation=conv, role=Message.Role.USER, content=message)
        Conversation.objects.filter(pk=conv.pk).update(
            message_count=conv.messages.count(), last_message_at=timezone.now()
        )

        perms = user_permissions(request.user, hostel, request=request)
        token = mint_context_token(
            hostel=hostel, user=request.user, perms=perms, conversation_id=conv.id
        )

        record_event(
            request,
            action=AuditEvent.Action.CREATE,
            actor=request.user,
            hostel=hostel,
            entity_type="ai.conversation",
            entity_id=conv.id,
            message="AI chat message sent",
            meta={"agent": conv.agent},
        )

        return Response(
            {
                "conversation_id": str(conv.id),
                "stream_url": f"{_stream_base()}/v1/chat/stream",
                "token": token,
                "expires_in": settings.ML_TOKEN_TTL,
            },
            status=status.HTTP_201_CREATED,
        )


class AiFeedbackView(APIView):
    """Capture 👍/👎 feedback on a conversation's latest answer (Phase 6 drift loop).

    Stored on the answer's AiUsage.meta (no schema change) so `ai_eval_export`
    can turn thumbs-down answers into eval cases — closing the quality-drift loop.
    """

    permission_classes = [IsHostelResolved, ActionPermissions, CHAT_FEATURE]
    permission_map = {"post": ["ai.chat"]}

    def post(self, request, pk):
        hostel = request.hostel
        conv = get_object_or_404(Conversation, pk=pk, hostel=hostel, user=request.user)
        rating = (request.data.get("rating") or "").lower()
        if rating not in ("up", "down"):
            raise ValidationError({"rating": "Must be 'up' or 'down'."})
        note = (request.data.get("note") or "")[:500]

        usage = (
            AiUsage.objects.filter(hostel=hostel, conversation=conv)
            .order_by("-created_at")
            .first()
        )
        if usage is None:
            raise ValidationError({"detail": "No AI answer to rate yet."})
        meta = usage.meta or {}
        meta["feedback"] = {"rating": rating, "note": note, "at": timezone.now().isoformat()}
        usage.meta = meta
        usage.save(update_fields=["meta"])
        return Response({"ok": True}, status=status.HTTP_200_OK)


class ConversationViewSet(viewsets.ReadOnlyModelViewSet):
    """List / read the caller's own conversations (+ archive & delete)."""

    permission_classes = [IsHostelResolved, ActionPermissions, CHAT_FEATURE]
    permission_map = {
        "list": ["ai.view"],
        "retrieve": ["ai.view"],
        "archive": ["ai.chat"],
        "destroy": ["ai.chat"],
    }

    def get_queryset(self):
        return Conversation.objects.filter(
            hostel=self.request.hostel, user=self.request.user
        ).prefetch_related("messages")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ConversationDetailSerializer
        return ConversationSerializer

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AiConfigView(APIView):
    """Whether AI is available to this workspace + what the UI needs to render."""

    permission_classes = [IsHostelResolved, ActionPermissions, CHAT_FEATURE]
    permission_map = {"get": ["ai.view"]}

    def get(self, request):
        perms = user_permissions(request.user, request.hostel, request=request)
        role = getattr(request.user, "role", "") or ""
        return Response(
            {
                "enabled": True,
                "stream_base": _stream_base(),
                "tools": tools.tools_for(perms, role),
            }
        )


class AiDashboardView(APIView):
    """KPI widgets for the AI dashboard, computed from ``AiUsage``."""

    permission_classes = [IsHostelResolved, ActionPermissions, CHAT_FEATURE]
    permission_map = {"get": ["ai.view"]}

    def get(self, request):
        from django.db.models import Avg, Count, Sum

        hostel = request.hostel
        today = timezone.localdate()
        usage = AiUsage.objects.filter(hostel=hostel)
        today_usage = usage.filter(created_at__date=today)

        agg = today_usage.aggregate(
            requests=Count("id"),
            tokens=Sum("tokens_total"),
            avg_latency=Avg("latency_ms"),
            cost=Sum("cost_usd"),
        )
        by_model = list(
            usage.values("model").annotate(requests=Count("id")).order_by("-requests")[:5]
        )
        return Response(
            {
                "requests_today": agg["requests"] or 0,
                "tokens_today": agg["tokens"] or 0,
                "avg_latency_ms": round(agg["avg_latency"] or 0),
                "estimated_cost_usd": str(agg["cost"] or 0),
                "active_conversations": Conversation.objects.filter(
                    hostel=hostel, is_archived=False
                ).count(),
                "total_requests": usage.count(),
                "model_usage": [
                    {"model": m["model"] or "unknown", "requests": m["requests"]} for m in by_model
                ],
            }
        )


# --------------------------------------------------------------------------- #
# Service-facing (Bearer context token)
# --------------------------------------------------------------------------- #
class _MlContextMixin:
    """Resolve the tenant + actor claims from the verified context token."""

    authentication_classes = []
    permission_classes = [IsMlContext]

    def _hostel(self, request):
        from apps.tenants.models import Hostel

        return get_object_or_404(Hostel, pk=request.ml_ctx["tid"])


class ConversationContextView(_MlContextMixin, APIView):
    """The service reads recent turns + workspace facts to build its prompt."""

    def get(self, request, pk):
        ctx = request.ml_ctx
        hostel = self._hostel(request)
        conv = get_object_or_404(Conversation, pk=pk, hostel=hostel)
        msgs = (
            conv.messages.exclude(role=Message.Role.SYSTEM)
            .order_by("-created_at")[:CONTEXT_MESSAGE_LIMIT]
        )
        history = [
            {"role": m.role, "content": m.content}
            for m in reversed(list(msgs))
        ]
        return Response(
            {
                "conversation_id": str(conv.id),
                "hostel": {"id": str(hostel.id), "name": ctx.get("tname", "")},
                "actor": {"role": ctx.get("role", "")},
                "messages": history,
                "tools": tools.tools_for(ctx.get("perms", []), ctx.get("role", "")),
            }
        )


class ConversationCompleteView(_MlContextMixin, APIView):
    """The service writes back the finished assistant turn + usage accounting."""

    def post(self, request, pk):
        ctx = request.ml_ctx
        hostel = self._hostel(request)
        conv = get_object_or_404(Conversation, pk=pk, hostel=hostel)
        data = request.data

        content = data.get("content") or ""
        provider = data.get("provider") or ""
        model = data.get("model") or ""
        tokens_prompt = int(data.get("tokens_prompt") or 0)
        tokens_completion = int(data.get("tokens_completion") or 0)
        latency_ms = int(data.get("latency_ms") or 0)
        tool_calls = data.get("tool_calls") or []
        sources = data.get("sources") or []
        error = data.get("error") or ""
        prompt_version = data.get("prompt_version") or ""

        msg = Message.objects.create(
            conversation=conv,
            role=Message.Role.ASSISTANT,
            content=content,
            tool_calls=tool_calls,
            provider=provider,
            model=model,
            tokens_prompt=tokens_prompt,
            tokens_completion=tokens_completion,
            latency_ms=latency_ms,
            error=error,
        )
        Conversation.objects.filter(pk=conv.pk).update(
            message_count=conv.messages.count(),
            last_message_at=timezone.now(),
            provider=provider,
            model=model,
        )
        # Estimate spend for paid providers (self-hosted stays 0); prefer an
        # explicit cost from the service if it sent one.
        incoming_cost = data.get("cost_usd")
        cost_usd = (
            Decimal(str(incoming_cost)) if incoming_cost not in (None, "")
            else metrics.estimate_cost(provider, model, tokens_prompt, tokens_completion)
        )
        success = not error

        AiUsage.objects.create(
            hostel=hostel,
            user_id=ctx.get("uid"),
            conversation=conv,
            kind=AiUsage.Kind.CHAT,
            provider=provider,
            model=model,
            tokens_prompt=tokens_prompt,
            tokens_completion=tokens_completion,
            tokens_total=tokens_prompt + tokens_completion,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            success=success,
            meta={
                "tool_calls": [t.get("name") for t in tool_calls if isinstance(t, dict)],
                "sources": sources,
                "prompt_version": prompt_version,  # AI/MLOps attribution (Phase 6)
            },
        )
        # First-class Prometheus series for the AI layer (no-op if unavailable).
        metrics.record_ai_usage(
            provider=provider, model=model, kind=AiUsage.Kind.CHAT, success=success,
            tokens_prompt=tokens_prompt, tokens_completion=tokens_completion,
            cost_usd=cost_usd, latency_ms=latency_ms,
        )
        return Response({"message_id": str(msg.id)}, status=status.HTTP_201_CREATED)


class ToolListView(_MlContextMixin, APIView):
    """Advertise the tools this caller may use (schemas for the LLM)."""

    def get(self, request):
        ctx = request.ml_ctx
        return Response({"tools": tools.tools_for(ctx.get("perms", []), ctx.get("role", ""))})


class ToolRunView(_MlContextMixin, APIView):
    """Execute one read-only tool against the caller's workspace."""

    def post(self, request, name):
        ctx = request.ml_ctx
        hostel = self._hostel(request)
        try:
            result = tools.run_tool(
                name, hostel, request.data or {}, ctx.get("perms", []), ctx.get("role", "")
            )
        except KeyError:
            return Response({"detail": f"Unknown tool: {name}"}, status=status.HTTP_404_NOT_FOUND)
        except PermissionError:
            return Response(
                {"detail": "Tool not permitted for this caller."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response({"tool": name, "result": result})
