"""AI guardrail tests (Phase 6 AI/MLOps)."""
from decimal import Decimal

import pytest
from django.test import override_settings
from rest_framework.exceptions import ValidationError

from .guardrails import (
    AiBudgetExceeded,
    check_daily_budget,
    check_input,
    enforce_pre_chat,
)
from .models import AiUsage

pytestmark = pytest.mark.django_db


@override_settings(AI_MAX_INPUT_CHARS=100)
def test_check_input_rejects_oversized():
    with pytest.raises(ValidationError):
        check_input("x" * 101)


@override_settings(AI_MAX_INPUT_CHARS=100)
def test_check_input_allows_within_limit():
    check_input("x" * 100)  # no raise


@override_settings(AI_DAILY_COST_BUDGET_USD=0)
def test_budget_disabled_by_default(hostel):
    AiUsage.objects.create(hostel=hostel, cost_usd=Decimal("99"))
    check_daily_budget(hostel)  # 0 = disabled, never raises


@override_settings(AI_DAILY_COST_BUDGET_USD="1.00")
def test_budget_blocks_when_exceeded(hostel):
    AiUsage.objects.create(hostel=hostel, cost_usd=Decimal("0.60"))
    AiUsage.objects.create(hostel=hostel, cost_usd=Decimal("0.60"))  # total 1.20 > 1.00
    with pytest.raises(AiBudgetExceeded):
        check_daily_budget(hostel)


@override_settings(AI_DAILY_COST_BUDGET_USD="5.00")
def test_budget_allows_under_limit(hostel):
    AiUsage.objects.create(hostel=hostel, cost_usd=Decimal("1.00"))
    check_daily_budget(hostel)  # under budget


@override_settings(AI_MAX_INPUT_CHARS=50, AI_DAILY_COST_BUDGET_USD=0)
def test_enforce_pre_chat_combines(hostel):
    with pytest.raises(ValidationError):
        enforce_pre_chat(message="y" * 51, hostel=hostel)
