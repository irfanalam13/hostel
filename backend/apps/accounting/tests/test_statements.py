"""Statement builders: trial balance, P&L and balance sheet all balance from
the same posted ledger."""
import datetime as dt
from decimal import Decimal

import pytest

from apps.accounting import services, statements
from apps.accounting.coa import seed_default_accounts
from apps.accounting.models import Account, JournalEntry

pytestmark = pytest.mark.django_db

TODAY = dt.date.today()


@pytest.fixture
def user(make_user, hostel):
    return make_user(role="ACCOUNTANT", hostel=hostel)


@pytest.fixture
def coa(hostel):
    seed_default_accounts(hostel)
    return {a.code: a for a in Account.objects.filter(hostel=hostel)}


@pytest.fixture
def books(hostel, user, coa):
    """A small set of transactions: capital injection, revenue, expense."""
    def post(dr, cr, amount):
        services.create_journal(
            hostel=hostel, actor=user,
            lines=[
                {"account": coa[dr], "debit": Decimal(amount), "credit": Decimal("0")},
                {"account": coa[cr], "debit": Decimal("0"), "credit": Decimal(amount)},
            ],
            status=JournalEntry.Status.POSTED,
        )
    post("1110", "3100", "10000.00")  # owner injects 10k cash
    post("1110", "4100", "3000.00")   # earn 3k fees
    post("5100", "1110", "1200.00")   # pay 1.2k salaries
    return coa


class TestTrialBalance:
    def test_debits_equal_credits(self, hostel, books):
        tb = statements.trial_balance(hostel, as_of=TODAY)
        assert tb["balanced"]
        assert Decimal(tb["total_debit"]) == Decimal(tb["total_credit"])
        assert Decimal(tb["total_debit"]) > 0


class TestProfitAndLoss:
    def test_net_profit(self, hostel, books):
        pl = statements.profit_and_loss(hostel, start=dt.date(2000, 1, 1), end=TODAY)
        assert pl["total_income"] == "3000.00"
        assert pl["total_expenses"] == "1200.00"
        assert pl["net_profit"] == "1800.00"


class TestBalanceSheet:
    def test_accounting_equation_holds(self, hostel, books):
        bs = statements.balance_sheet(hostel, as_of=TODAY)
        assert bs["balanced"]
        # Assets = cash 11,800 (10k + 3k − 1.2k)
        assert bs["total_assets"] == "11800.00"
        # Equity = capital 10k + current-year earnings 1.8k
        assert Decimal(bs["total_liabilities_equity"]) == Decimal(bs["total_assets"])

    def test_cash_flow_ending_matches_cash(self, hostel, books):
        cf = statements.cash_flow(hostel, start=dt.date(2000, 1, 1), end=TODAY)
        assert cf["ending_cash"] == "11800.00"


class TestGeneralLedger:
    def test_running_balance(self, hostel, books):
        gl = statements.general_ledger(hostel, books["1110"])
        assert gl["closing_balance"] == "11800.00"
        assert gl["rows"][-1]["balance"] == "11800.00"


class TestStatementOfEquity:
    def test_closing_ties_to_balance_sheet(self, hostel, books):
        soe = statements.statement_of_equity(hostel, start=dt.date(2000, 1, 1), end=TODAY)
        # Owner capital 10k + current-year earnings 1.8k.
        assert soe["net_income"] == "1800.00"
        assert soe["closing_equity"] == "11800.00"
        bs = statements.balance_sheet(hostel, as_of=TODAY)
        assert Decimal(soe["closing_equity"]) == Decimal(bs["total_equity"])
        codes = {c["code"] for c in soe["components"]}
        assert "3100" in codes and "3300" in codes


class TestMonthlyTrends:
    def test_current_month_flows(self, hostel, books):
        tr = statements.monthly_trends(hostel, end=TODAY, months=12)
        assert len(tr["series"]) == 12
        last = tr["series"][-1]
        assert last["revenue"] == "3000.00"
        assert last["expenses"] == "1200.00"
        assert last["profit"] == "1800.00"
        # Cash: +10k +3k in, -1.2k out.
        assert last["cash_in"] == "13000.00"
        assert last["cash_out"] == "1200.00"
        assert last["net_cash"] == "11800.00"

    def test_window_length_configurable(self, hostel, books):
        assert len(statements.monthly_trends(hostel, end=TODAY, months=6)["series"]) == 6
