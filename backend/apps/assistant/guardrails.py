"""AI guardrails enforced at the gateway choke point (Phase 6 AI/MLOps).

The gateway is the one place every chat turn passes through, so input and
budget limits belong here — before a token is spent or a context token is
minted. RBAC/tenant-scoping guardrails already live in the tool layer
(apps.assistant.tools + the signed context token); this module adds:

  * input size cap  — reject oversized prompts (abuse / cost / context blowup)
  * daily cost budget — a per-tenant spend ceiling on top of the plan's monthly
    request quota (``_check_quota`` in views), using the estimated cost we now
    record on every AiUsage (Phase 4).

Limits are settings-driven with safe defaults, so they work without config
changes and are overridable per deploy / in tests.
"""
from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from .models import AiUsage


class AiBudgetExceeded(APIException):
    status_code = 429
    default_detail = "The AI budget for today has been reached. Try again tomorrow."
    default_code = "ai_budget_exceeded"


def max_input_chars() -> int:
    return int(getattr(settings, "AI_MAX_INPUT_CHARS", 8000))


def daily_cost_budget_usd() -> Decimal:
    # 0 (default) disables the budget guardrail.
    return Decimal(str(getattr(settings, "AI_DAILY_COST_BUDGET_USD", 0)))


def check_input(message: str) -> None:
    """Reject an oversized prompt before it reaches the model."""
    limit = max_input_chars()
    if len(message) > limit:
        raise ValidationError(
            {"message": f"Message is too long ({len(message)} chars); limit is {limit}."}
        )


def check_daily_budget(hostel) -> None:
    """Block new turns once today's estimated spend hits the tenant budget."""
    budget = daily_cost_budget_usd()
    if budget <= 0:
        return  # disabled
    today = timezone.localdate()
    spent = AiUsage.objects.filter(
        hostel=hostel, created_at__date=today
    ).aggregate(total=Sum("cost_usd"))["total"] or Decimal("0")
    if spent >= budget:
        raise AiBudgetExceeded(
            f"Daily AI budget of ${budget} reached (spent ${spent})."
        )


def enforce_pre_chat(*, message: str, hostel) -> None:
    """All pre-chat guardrails in one call for the gateway view."""
    check_input(message)
    check_daily_budget(hostel)
