"""Double-entry engine correctness: balanced posting, immutability, reversal,
period locking, opening balances, year-end close and depreciation."""
import datetime as dt
from decimal import Decimal

import pytest
from rest_framework.exceptions import ValidationError

from apps.accounting import services, statements
from apps.accounting.coa import seed_default_accounts
from apps.accounting.models import (
    Account,
    AccountingPeriod,
    FiscalYear,
    FixedAsset,
    JournalEntry,
    LedgerEntry,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def user(make_user, hostel):
    return make_user(role="ACCOUNTANT", hostel=hostel)


@pytest.fixture
def coa(hostel):
    seed_default_accounts(hostel)
    return {a.code: a for a in Account.objects.filter(hostel=hostel)}


def _lines(coa, dr_code, cr_code, amount):
    return [
        {"account": coa[dr_code], "debit": Decimal(amount), "credit": Decimal("0")},
        {"account": coa[cr_code], "debit": Decimal("0"), "credit": Decimal(amount)},
    ]


class TestChartOfAccounts:
    def test_seed_is_idempotent_and_linked(self, hostel):
        n1 = seed_default_accounts(hostel)
        n2 = seed_default_accounts(hostel)
        assert n1 > 0 and n2 == 0
        cash = Account.objects.get(hostel=hostel, code="1110")
        assert cash.type == "asset"
        assert cash.parent.code == "1100"  # Current Assets
        assert cash.normal_balance == "debit"

    def test_income_account_is_credit_normal(self, coa):
        assert coa["4100"].normal_balance == "credit"


class TestJournalPosting:
    def test_balanced_journal_posts_to_ledger(self, hostel, user, coa):
        journal = services.create_journal(
            hostel=hostel, actor=user,
            lines=_lines(coa, "1110", "4100", "1000.00"),  # Dr Cash, Cr Student Fees
            status=JournalEntry.Status.POSTED,
        )
        assert journal.status == JournalEntry.Status.POSTED
        assert journal.number.startswith("JV-")
        assert journal.is_locked
        assert LedgerEntry.objects.filter(journal=journal).count() == 2
        assert statements.account_balance(hostel, coa["1110"], as_of=dt.date.today()) == Decimal("1000.00")

    def test_unbalanced_journal_rejected(self, hostel, user, coa):
        with pytest.raises(ValidationError):
            services.create_journal(
                hostel=hostel, actor=user,
                lines=[
                    {"account": coa["1110"], "debit": "1000", "credit": "0"},
                    {"account": coa["4100"], "debit": "0", "credit": "900"},
                ],
            )

    def test_line_cannot_be_both_sides(self, hostel, user, coa):
        with pytest.raises(ValidationError):
            services.validate_lines([
                {"account": coa["1110"], "debit": "100", "credit": "100"},
                {"account": coa["4100"], "debit": "0", "credit": "100"},
            ])

    def test_cannot_post_to_group_account(self, hostel, user, coa):
        with pytest.raises(ValidationError):
            services.create_journal(
                hostel=hostel, actor=user,
                lines=_lines(coa, "1000", "4100", "100.00"),  # 1000 = Assets (group)
                status=JournalEntry.Status.POSTED,
            )

    def test_posted_journal_is_immutable(self, hostel, user, coa):
        journal = services.create_journal(
            hostel=hostel, actor=user, lines=_lines(coa, "1110", "4100", "500.00"),
            status=JournalEntry.Status.POSTED,
        )
        with pytest.raises(ValidationError):
            services.replace_lines(journal, _lines(coa, "1110", "4100", "999.00"))


class TestWorkflow:
    def test_full_workflow(self, hostel, user, coa):
        j = services.create_journal(hostel=hostel, actor=user, lines=_lines(coa, "1110", "4100", "200"))
        assert j.status == "draft"
        services.submit_journal(j, actor=user)
        assert j.status == "submitted"
        services.approve_journal(j, actor=user)
        assert j.status == "approved"
        services.post_journal(j, actor=user)
        assert j.status == "posted"


class TestReversal:
    def test_reversal_nets_to_zero(self, hostel, user, coa):
        j = services.create_journal(
            hostel=hostel, actor=user, lines=_lines(coa, "1110", "4100", "750.00"),
            status=JournalEntry.Status.POSTED,
        )
        reversal = services.reverse_journal(j, actor=user)
        j.refresh_from_db()
        assert j.status == "reversed"
        assert reversal.journal_type == "reversal"
        # Cash nets back to zero.
        assert statements.account_balance(hostel, coa["1110"], as_of=dt.date.today()) == Decimal("0.00")

    def test_cannot_reverse_twice(self, hostel, user, coa):
        j = services.create_journal(
            hostel=hostel, actor=user, lines=_lines(coa, "1110", "4100", "10.00"),
            status=JournalEntry.Status.POSTED,
        )
        services.reverse_journal(j, actor=user)
        with pytest.raises(ValidationError):
            services.reverse_journal(j, actor=user)


class TestPeriodLocking:
    @pytest.fixture
    def fiscal(self, hostel):
        fy = FiscalYear.objects.create(
            hostel=hostel, name="FY26", start_date=dt.date(2026, 1, 1), end_date=dt.date(2026, 12, 31)
        )
        period = AccountingPeriod.objects.create(
            hostel=hostel, fiscal_year=fy, name="2026-01",
            start_date=dt.date(2026, 1, 1), end_date=dt.date(2026, 1, 31),
        )
        return fy, period

    def test_cannot_post_into_closed_period(self, hostel, user, coa, fiscal):
        _fy, period = fiscal
        services.close_period(period)
        with pytest.raises(ValidationError):
            services.create_journal(
                hostel=hostel, actor=user,
                lines=_lines(coa, "1110", "4100", "100.00"),
                status=JournalEntry.Status.POSTED,
                date=dt.date(2026, 1, 15),
            )

    def test_can_post_after_reopen(self, hostel, user, coa, fiscal):
        _fy, period = fiscal
        services.close_period(period)
        services.reopen_period(period)
        j = services.create_journal(
            hostel=hostel, actor=user, lines=_lines(coa, "1110", "4100", "100.00"),
            status=JournalEntry.Status.POSTED, date=dt.date(2026, 1, 15),
        )
        assert j.status == "posted"
        assert j.period_id == period.id


class TestOpeningBalancesAndClose:
    def test_opening_balances_post_balanced(self, hostel, user, coa):
        coa["1110"].opening_balance = Decimal("5000.00")  # Dr cash
        coa["1110"].save()
        coa["3100"].opening_balance = Decimal("-5000.00")  # Cr capital
        coa["3100"].save()
        fy = FiscalYear.objects.create(
            hostel=hostel, name="FY26", start_date=dt.date(2026, 1, 1), end_date=dt.date(2026, 12, 31)
        )
        journal = services.post_opening_balances(hostel=hostel, actor=user, fiscal_year=fy)
        assert journal.is_balanced
        tb = statements.trial_balance(hostel, as_of=dt.date(2026, 1, 1))
        assert tb["balanced"]

    def test_year_close_moves_pl_to_retained_earnings(self, hostel, user, coa):
        fy = FiscalYear.objects.create(
            hostel=hostel, name="FY26", start_date=dt.date(2026, 1, 1), end_date=dt.date(2026, 12, 31)
        )
        # Earn 2000 revenue, spend 500.
        services.create_journal(
            hostel=hostel, actor=user, lines=_lines(coa, "1110", "4100", "2000.00"),
            status=JournalEntry.Status.POSTED, date=dt.date(2026, 6, 1),
        )
        services.create_journal(
            hostel=hostel, actor=user, lines=_lines(coa, "5100", "1110", "500.00"),
            status=JournalEntry.Status.POSTED, date=dt.date(2026, 6, 2),
        )
        services.close_fiscal_year(hostel=hostel, actor=user, fiscal_year=fy)
        fy.refresh_from_db()
        assert fy.is_closed
        # Income/expense accounts zeroed; retained earnings holds net 1500.
        assert statements.account_balance(hostel, coa["4100"], as_of=dt.date(2026, 12, 31)) == Decimal("0.00")
        assert statements.account_balance(hostel, coa["5100"], as_of=dt.date(2026, 12, 31)) == Decimal("0.00")
        retained = statements.account_balance(hostel, coa["3200"], as_of=dt.date(2026, 12, 31))
        assert retained == Decimal("-1500.00")  # credit balance (equity)


class TestDepreciation:
    def test_straight_line_depreciation(self, hostel, user, coa):
        asset = FixedAsset.objects.create(
            hostel=hostel, name="Laptop", purchase_cost=Decimal("1200.00"),
            purchase_date=dt.date(2026, 1, 1), useful_life_months=12, salvage_value=Decimal("0"),
            depreciation_method=FixedAsset.DepreciationMethod.STRAIGHT_LINE,
        )
        services.run_depreciation(hostel=hostel, actor=user, asset=asset)
        asset.refresh_from_db()
        assert asset.accumulated_depreciation == Decimal("100.00")  # 1200/12
        assert asset.net_book_value == Decimal("1100.00")
        # Depreciation expense hit the P&L account 5190.
        assert statements.account_balance(hostel, coa["5190"], as_of=dt.date.today()) == Decimal("100.00")
