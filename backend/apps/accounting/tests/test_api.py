"""Accounting API: end-to-end through the full auth + tenant + RBAC stack, plus
cross-tenant isolation and permission enforcement."""

import datetime as dt

import pytest

from apps.accounting.coa import seed_default_accounts
from apps.accounting.models import Account, JournalEntry, LedgerEntry

TODAY = dt.date.today()

pytestmark = pytest.mark.django_db

BASE = "/api/accounting"


def _data(resp):
    return resp.json()["data"]


@pytest.fixture
def accountant_client(auth_client, accountant, hostel):
    return auth_client(accountant, hostel)


@pytest.fixture
def warden_client(auth_client, warden, hostel):
    return auth_client(warden, hostel)


@pytest.fixture
def coa(hostel):
    seed_default_accounts(hostel)
    return {a.code: a for a in Account.objects.filter(hostel=hostel)}


def _journal_payload(coa, amount="1000.00", post=False):
    return {
        "description": "Test entry",
        "post": post,
        "lines": [
            {"account": str(coa["1110"].id), "debit": amount, "credit": "0"},
            {"account": str(coa["4100"].id), "debit": "0", "credit": amount},
        ],
    }


class TestChartOfAccountsApi:
    def test_list_seeds_defaults(self, accountant_client):
        rows = _data(accountant_client.get(f"{BASE}/accounts/"))
        assert any(a["code"] == "1110" for a in rows)

    def test_create_account_auto_code(self, accountant_client):
        resp = accountant_client.post(
            f"{BASE}/accounts/", {"name": "Custom Income", "type": "income"}, format="json"
        )
        assert resp.status_code == 201, resp.content
        assert _data(resp)["code"].startswith("4")

    def test_system_account_not_deletable(self, accountant_client, coa):
        # Ensure defaults are present through the API path.
        accountant_client.get(f"{BASE}/accounts/")
        cash = Account.objects.get(hostel=coa["1110"].hostel, code="1110")
        resp = accountant_client.delete(f"{BASE}/accounts/{cash.id}/")
        assert resp.status_code == 400


class TestJournalApi:
    def test_create_and_post_flow(self, accountant_client, coa):
        created = _data(accountant_client.post(
            f"{BASE}/journals/", _journal_payload(coa), format="json"
        ))
        assert created["status"] == "draft"
        assert created["total_debit"] == "1000.00"

        posted = _data(accountant_client.post(f"{BASE}/journals/{created['id']}/post/"))
        assert posted["status"] == "posted"
        assert LedgerEntry.objects.filter(journal_id=created["id"]).count() == 2

    def test_create_posted_directly(self, accountant_client, coa):
        resp = accountant_client.post(
            f"{BASE}/journals/", _journal_payload(coa, post=True), format="json"
        )
        assert _data(resp)["status"] == "posted"

    def test_unbalanced_rejected(self, accountant_client, coa):
        payload = _journal_payload(coa)
        payload["lines"][1]["credit"] = "900.00"
        resp = accountant_client.post(f"{BASE}/journals/", payload, format="json")
        assert resp.status_code == 400

    def test_posted_journal_cannot_be_edited(self, accountant_client, coa):
        j = _data(accountant_client.post(
            f"{BASE}/journals/", _journal_payload(coa, post=True), format="json"
        ))
        resp = accountant_client.patch(
            f"{BASE}/journals/{j['id']}/", {"description": "x"}, format="json"
        )
        assert resp.status_code == 400

    def test_reverse(self, accountant_client, coa):
        j = _data(accountant_client.post(
            f"{BASE}/journals/", _journal_payload(coa, post=True), format="json"
        ))
        resp = accountant_client.post(f"{BASE}/journals/{j['id']}/reverse/")
        assert resp.status_code == 200
        assert _data(resp)["journal_type"] == "reversal"


class TestFiscalYearApi:
    def test_generate_periods_and_close(self, accountant_client):
        fy = _data(accountant_client.post(
            f"{BASE}/fiscal-years/",
            {"name": "FY 2026", "start_date": "2026-01-01", "end_date": "2026-12-31"},
            format="json",
        ))
        resp = accountant_client.post(f"{BASE}/fiscal-years/{fy['id']}/generate-periods/")
        assert resp.status_code == 200
        assert len(_data(resp)["periods"]) == 12

        resp = accountant_client.post(f"{BASE}/fiscal-years/{fy['id']}/close/")
        assert _data(resp)["is_closed"] is True


class TestReportsApi:
    def _seed_books(self, client, coa):
        for dr, cr, amt in [("1110", "3100", "10000.00"), ("1110", "4100", "3000.00"),
                            ("5100", "1110", "1200.00")]:
            client.post(f"{BASE}/journals/", {
                "post": True,
                "lines": [
                    {"account": str(coa[dr].id), "debit": amt, "credit": "0"},
                    {"account": str(coa[cr].id), "debit": "0", "credit": amt},
                ],
            }, format="json")

    def test_trial_balance_balanced(self, accountant_client, coa):
        self._seed_books(accountant_client, coa)
        tb = _data(accountant_client.get(f"{BASE}/reports/trial-balance/"))
        assert tb["balanced"]
        assert tb["total_debit"] == tb["total_credit"]

    def test_balance_sheet_and_pl(self, accountant_client, coa):
        self._seed_books(accountant_client, coa)
        bs = _data(accountant_client.get(f"{BASE}/reports/balance-sheet/"))
        assert bs["balanced"]
        assert bs["total_assets"] == "11800.00"
        pl = _data(accountant_client.get(
            f"{BASE}/reports/profit-loss/?start=2000-01-01&end=2100-01-01"
        ))
        assert pl["net_profit"] == "1800.00"

    def test_export_trial_balance_csv(self, accountant_client, coa):
        self._seed_books(accountant_client, coa)
        resp = accountant_client.get(f"{BASE}/reports/export/?type=trial-balance")
        assert resp.status_code == 200
        assert resp["Content-Type"] == "text/csv"
        assert "TOTAL" in resp.content.decode()

    def test_export_profit_loss_csv(self, accountant_client, coa):
        self._seed_books(accountant_client, coa)
        resp = accountant_client.get(f"{BASE}/reports/export/?type=profit-loss")
        assert resp.status_code == 200
        assert "Net Profit" in resp.content.decode()

    def test_statement_of_equity(self, accountant_client, coa):
        self._seed_books(accountant_client, coa)
        soe = _data(accountant_client.get(
            f"{BASE}/reports/statement-of-equity/?start=2000-01-01&end=2100-01-01"
        ))
        assert soe["closing_equity"] == "11800.00"
        assert soe["net_income"] == "1800.00"

    def test_trends(self, accountant_client, coa):
        self._seed_books(accountant_client, coa)
        tr = _data(accountant_client.get(f"{BASE}/reports/trends/?months=6"))
        assert len(tr["series"]) == 6
        assert tr["series"][-1]["profit"] == "1800.00"


class TestDashboardApi:
    def test_summary(self, accountant_client, coa):
        resp = accountant_client.get(f"{BASE}/dashboard/summary/")
        assert resp.status_code == 200
        assert "totals" in _data(resp)


class TestBudgetVariance:
    def _post_expense(self, client, coa, code, amount):
        client.post(f"{BASE}/journals/", {
            "post": True,
            "lines": [
                {"account": str(coa[code].id), "debit": amount, "credit": "0"},
                {"account": str(coa["1110"].id), "debit": "0", "credit": amount},
            ],
        }, format="json")

    def test_variance(self, accountant_client, coa):
        self._post_expense(accountant_client, coa, "5100", "1200.00")
        fy = _data(accountant_client.post(f"{BASE}/fiscal-years/", {
            "name": "FY current",
            "start_date": TODAY.replace(month=1, day=1).isoformat(),
            "end_date": TODAY.replace(month=12, day=31).isoformat(),
        }, format="json"))
        budget = _data(accountant_client.post(f"{BASE}/budgets/", {
            "name": "Ops budget", "fiscal_year": fy["id"], "period_type": "annual",
            "lines": [{"account": str(coa["5100"].id), "amount": "2000.00"}],
        }, format="json"))
        var = _data(accountant_client.get(f"{BASE}/budgets/{budget['id']}/variance/"))
        row = next(r for r in var["rows"] if r["code"] == "5100")
        assert row["budget"] == "2000.00"
        assert row["actual"] == "1200.00"
        assert row["variance"] == "800.00"   # under budget → favourable
        assert row["utilization"] == "60.00"


class TestBankReconciliation:
    def _bank_account(self, client, coa):
        return _data(client.post(f"{BASE}/bank-accounts/", {
            "name": "Main Bank", "account": str(coa["1130"].id),
        }, format="json"))

    def test_import_csv_and_auto_match(self, accountant_client, coa):
        bank = self._bank_account(accountant_client, coa)
        # A posted movement of 500 into the bank GL account.
        accountant_client.post(f"{BASE}/journals/", {
            "post": True,
            "lines": [
                {"account": str(coa["1130"].id), "debit": "500.00", "credit": "0"},
                {"account": str(coa["4100"].id), "debit": "0", "credit": "500.00"},
            ],
        }, format="json")

        csv_text = f"date,description,amount\n{TODAY.isoformat()},Deposit,500.00\n"
        imp = accountant_client.post(f"{BASE}/bank-statement-lines/import-csv/", {
            "bank_account": bank["id"], "content": csv_text,
        }, format="json")
        assert imp.status_code == 201, imp.content
        assert _data(imp)["imported"] == 1

        matched = _data(accountant_client.post(
            f"{BASE}/bank-accounts/{bank['id']}/auto-match/", {}, format="json"
        ))
        assert matched["matched"] == 1
        line = _data(accountant_client.get(
            f"{BASE}/bank-statement-lines/?bank_account={bank['id']}"
        ))[0]
        assert line["is_reconciled"] is True


class TestPermissions:
    def test_warden_cannot_access_accounting(self, warden_client):
        # WARDEN holds no accounting.* permission.
        assert warden_client.get(f"{BASE}/accounts/").status_code == 403
        assert warden_client.get(f"{BASE}/dashboard/summary/").status_code == 403

    def test_warden_cannot_post_journal(self, warden_client, accountant_client, coa):
        j = _data(accountant_client.post(
            f"{BASE}/journals/", _journal_payload(coa), format="json"
        ))
        assert warden_client.post(f"{BASE}/journals/{j['id']}/post/").status_code == 403

    def test_anonymous_denied(self, api):
        assert api.get(f"{BASE}/accounts/").status_code in (401, 403)


class TestIsolation:
    def test_other_tenant_journals_invisible(self, accountant_client, coa, other_hostel, make_user):
        other_actor = make_user(role="OWNER", hostel=other_hostel)
        seed_default_accounts(other_hostel)
        from apps.accounting import services

        other_coa = {a.code: a for a in Account.objects.filter(hostel=other_hostel)}
        services.create_journal(
            hostel=other_hostel, actor=other_actor,
            lines=[
                {"account": other_coa["1110"], "debit": "999.00", "credit": "0"},
                {"account": other_coa["4100"], "debit": "0", "credit": "999.00"},
            ],
            status=JournalEntry.Status.POSTED,
        )
        rows = _data(accountant_client.get(f"{BASE}/journals/"))
        assert rows == []
        # Our trial balance sees none of the other tenant's postings.
        tb = _data(accountant_client.get(f"{BASE}/reports/trial-balance/"))
        assert tb["rows"] == []

    def test_journal_cannot_reference_other_tenant_account(
        self, accountant_client, coa, other_hostel
    ):
        seed_default_accounts(other_hostel)
        foreign = Account.objects.filter(hostel=other_hostel, code="4100").first()
        payload = {
            "lines": [
                {"account": str(coa["1110"].id), "debit": "100.00", "credit": "0"},
                {"account": str(foreign.id), "debit": "0", "credit": "100.00"},
            ],
        }
        resp = accountant_client.post(f"{BASE}/journals/", payload, format="json")
        assert resp.status_code == 400
