"""Financial statement builders — derived purely from posted ``LedgerEntry``
rows, so every statement balances by construction.

Conventions:

- ``account_activity(account, start, end)`` → ``(debit, credit)`` totals in a
  date range.
- Balance-sheet figures are cumulative "as of" a date (from inception).
- Income-statement figures are period flows (a date range).
- Signed balances are debit-positive: ``balance = Σdebit − Σcredit``.
"""
from decimal import Decimal

from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce, TruncMonth

from .models import Account, AccountType, LedgerEntry

ZERO = Decimal("0.00")
_MONEY = DecimalField(max_digits=18, decimal_places=2)


def _sum(qs):
    return qs.aggregate(
        d=Coalesce(Sum("debit"), Value(ZERO, output_field=_MONEY)),
        c=Coalesce(Sum("credit"), Value(ZERO, output_field=_MONEY)),
    )


def _base_qs(hostel, *, branch=None, cost_center=None):
    qs = LedgerEntry.objects.filter(hostel=hostel)
    if branch is not None:
        qs = qs.filter(branch=branch)
    if cost_center is not None:
        qs = qs.filter(cost_center=cost_center)
    return qs


def account_activity(hostel, account, start, end, *, branch=None, cost_center=None):
    """(debit, credit) totals posted to an account within [start, end]."""
    qs = _base_qs(hostel, branch=branch, cost_center=cost_center).filter(
        account=account, date__gte=start, date__lte=end
    )
    agg = _sum(qs)
    return agg["d"], agg["c"]


def account_balance(hostel, account, *, as_of=None, branch=None, cost_center=None) -> Decimal:
    """Signed (debit-positive) cumulative balance of an account as of a date."""
    qs = _base_qs(hostel, branch=branch, cost_center=cost_center).filter(account=account)
    if as_of is not None:
        qs = qs.filter(date__lte=as_of)
    agg = _sum(qs)
    return (agg["d"] - agg["c"]).quantize(ZERO)


# --------------------------------------------------------------------------- #
# Per-account balances in bulk (one query) for statements
# --------------------------------------------------------------------------- #
def _balances_by_account(hostel, *, start=None, end=None, branch=None, cost_center=None):
    """Map account_id → (debit_total, credit_total) over an optional range."""
    qs = _base_qs(hostel, branch=branch, cost_center=cost_center)
    if start is not None:
        qs = qs.filter(date__gte=start)
    if end is not None:
        qs = qs.filter(date__lte=end)
    rows = qs.values("account_id").annotate(
        d=Coalesce(Sum("debit"), Value(ZERO, output_field=_MONEY)),
        c=Coalesce(Sum("credit"), Value(ZERO, output_field=_MONEY)),
    )
    return {r["account_id"]: (r["d"], r["c"]) for r in rows}


# --------------------------------------------------------------------------- #
# Trial balance
# --------------------------------------------------------------------------- #
def trial_balance(hostel, *, as_of, branch=None, cost_center=None):
    """Every posting account's net position as of a date, split into debit/credit
    columns. Total debit always equals total credit."""
    balances = _balances_by_account(hostel, end=as_of, branch=branch, cost_center=cost_center)
    accounts = {
        a.id: a
        for a in Account.objects.filter(hostel=hostel, is_group=False).only(
            "id", "code", "name", "type"
        )
    }
    rows = []
    total_debit = ZERO
    total_credit = ZERO
    for acc_id, (debit, credit) in balances.items():
        account = accounts.get(acc_id)
        if account is None:
            continue
        net = debit - credit  # debit-positive
        if net == 0:
            continue
        debit_col = net if net > 0 else ZERO
        credit_col = -net if net < 0 else ZERO
        total_debit += debit_col
        total_credit += credit_col
        rows.append({
            "account_id": str(acc_id),
            "code": account.code,
            "name": account.name,
            "type": account.type,
            "debit": str(debit_col.quantize(ZERO)),
            "credit": str(credit_col.quantize(ZERO)),
        })
    rows.sort(key=lambda r: r["code"])
    return {
        "as_of": as_of,
        "rows": rows,
        "total_debit": str(total_debit.quantize(ZERO)),
        "total_credit": str(total_credit.quantize(ZERO)),
        "balanced": total_debit == total_credit,
    }


# --------------------------------------------------------------------------- #
# Profit & loss
# --------------------------------------------------------------------------- #
def profit_and_loss(hostel, *, start, end, branch=None, cost_center=None):
    """Income-statement flow over [start, end]. Income shown as credit-positive,
    expenses as debit-positive; net profit = income − expenses."""
    balances = _balances_by_account(
        hostel, start=start, end=end, branch=branch, cost_center=cost_center
    )
    accounts = {
        a.id: a
        for a in Account.objects.filter(
            hostel=hostel, is_group=False, type__in=[AccountType.INCOME, AccountType.EXPENSE]
        ).only("id", "code", "name", "type", "subtype")
    }
    income_rows, expense_rows = [], []
    total_income = ZERO
    total_expense = ZERO
    for acc_id, (debit, credit) in balances.items():
        account = accounts.get(acc_id)
        if account is None:
            continue
        if account.type == AccountType.INCOME:
            amount = (credit - debit).quantize(ZERO)
            if amount == 0:
                continue
            total_income += amount
            income_rows.append(_stmt_row(account, amount))
        else:
            amount = (debit - credit).quantize(ZERO)
            if amount == 0:
                continue
            total_expense += amount
            expense_rows.append(_stmt_row(account, amount))
    income_rows.sort(key=lambda r: r["code"])
    expense_rows.sort(key=lambda r: r["code"])
    net = total_income - total_expense
    return {
        "start": start,
        "end": end,
        "income": income_rows,
        "expenses": expense_rows,
        "total_income": str(total_income.quantize(ZERO)),
        "total_expenses": str(total_expense.quantize(ZERO)),
        "net_profit": str(net.quantize(ZERO)),
    }


def _stmt_row(account, amount: Decimal):
    return {
        "account_id": str(account.id),
        "code": account.code,
        "name": account.name,
        "subtype": account.subtype,
        "amount": str(amount.quantize(ZERO)),
    }


# --------------------------------------------------------------------------- #
# Balance sheet
# --------------------------------------------------------------------------- #
def balance_sheet(hostel, *, as_of, branch=None, cost_center=None):
    """Snapshot of assets, liabilities and equity as of a date. Net income for
    the period-to-date is folded into equity so Assets = Liabilities + Equity."""
    balances = _balances_by_account(hostel, end=as_of, branch=branch, cost_center=cost_center)
    accounts = {
        a.id: a
        for a in Account.objects.filter(hostel=hostel, is_group=False).only(
            "id", "code", "name", "type", "subtype"
        )
    }

    assets, liabilities, equity = [], [], []
    total_assets = ZERO
    total_liabilities = ZERO
    total_equity = ZERO
    net_income = ZERO  # credit-positive

    for acc_id, (debit, credit) in balances.items():
        account = accounts.get(acc_id)
        if account is None:
            continue
        if account.type == AccountType.ASSET:
            amount = (debit - credit).quantize(ZERO)
            if amount != 0:
                total_assets += amount
                assets.append(_stmt_row(account, amount))
        elif account.type == AccountType.LIABILITY:
            amount = (credit - debit).quantize(ZERO)
            if amount != 0:
                total_liabilities += amount
                liabilities.append(_stmt_row(account, amount))
        elif account.type == AccountType.EQUITY:
            amount = (credit - debit).quantize(ZERO)
            if amount != 0:
                total_equity += amount
                equity.append(_stmt_row(account, amount))
        elif account.type == AccountType.INCOME:
            net_income += (credit - debit)
        elif account.type == AccountType.EXPENSE:
            net_income -= (debit - credit)

    net_income = net_income.quantize(ZERO)
    # Unclosed P&L flows into equity as "Current Year Earnings".
    if net_income != 0:
        equity.append({
            "account_id": None,
            "code": "3300",
            "name": "Current Year Earnings",
            "subtype": "retained",
            "amount": str(net_income),
        })
        total_equity += net_income

    for bucket in (assets, liabilities, equity):
        bucket.sort(key=lambda r: r["code"])

    total_liab_equity = total_liabilities + total_equity
    return {
        "as_of": as_of,
        "assets": assets,
        "liabilities": liabilities,
        "equity": equity,
        "total_assets": str(total_assets.quantize(ZERO)),
        "total_liabilities": str(total_liabilities.quantize(ZERO)),
        "total_equity": str(total_equity.quantize(ZERO)),
        "total_liabilities_equity": str(total_liab_equity.quantize(ZERO)),
        "balanced": total_assets == total_liab_equity,
    }


# --------------------------------------------------------------------------- #
# Cash flow (indirect-lite: movement on cash & bank accounts)
# --------------------------------------------------------------------------- #
def cash_flow(hostel, *, start, end, branch=None):
    """Cash movement over a range, grouped by the offsetting account type, plus
    beginning/ending cash. Uses cash & bank accounts (subtype cash/bank)."""
    cash_accounts = list(
        Account.objects.filter(
            hostel=hostel, is_group=False, type=AccountType.ASSET,
            subtype__in=["cash", "bank"],
        ).values_list("id", flat=True)
    )
    qs = _base_qs(hostel, branch=branch).filter(account_id__in=cash_accounts)

    def _net(entries):
        agg = _sum(entries)
        return (agg["d"] - agg["c"]).quantize(ZERO)

    beginning = _net(qs.filter(date__lt=start))
    period = qs.filter(date__gte=start, date__lte=end)
    movement = _net(period)
    inflow = _sum(period)["d"].quantize(ZERO)
    outflow = _sum(period)["c"].quantize(ZERO)
    ending = beginning + movement

    return {
        "start": start,
        "end": end,
        "beginning_cash": str(beginning),
        "inflow": str(inflow),
        "outflow": str(outflow),
        "net_change": str(movement),
        "ending_cash": str(ending),
    }


# --------------------------------------------------------------------------- #
# General ledger & dashboard
# --------------------------------------------------------------------------- #
def general_ledger(hostel, account, *, start=None, end=None, branch=None):
    """Running-balance ledger for one account over an optional range."""
    opening = ZERO
    if start is not None:
        opening = account_balance(hostel, account, as_of=_day_before(start), branch=branch)
    qs = _base_qs(hostel, branch=branch).filter(account=account).order_by("date", "created_at")
    if start is not None:
        qs = qs.filter(date__gte=start)
    if end is not None:
        qs = qs.filter(date__lte=end)

    running = opening
    rows = []
    for entry in qs.select_related("journal"):
        running += entry.debit - entry.credit
        rows.append({
            "id": str(entry.id),
            "date": entry.date,
            "journal_number": entry.journal.number,
            "description": entry.description,
            "debit": str(entry.debit.quantize(ZERO)),
            "credit": str(entry.credit.quantize(ZERO)),
            "balance": str(running.quantize(ZERO)),
        })
    return {
        "account": {"id": str(account.id), "code": account.code, "name": account.name,
                    "type": account.type, "normal_balance": account.normal_balance},
        "opening_balance": str(opening.quantize(ZERO)),
        "rows": rows,
        "closing_balance": str(running.quantize(ZERO)),
    }


def _day_before(d):
    from datetime import timedelta

    return d - timedelta(days=1)


def dashboard_snapshot(hostel, *, as_of, start, end, branch=None):
    """The accounting dashboard KPIs, derived from the statement builders."""
    bs = balance_sheet(hostel, as_of=as_of, branch=branch)
    pl = profit_and_loss(hostel, start=start, end=end, branch=branch)
    cf = cash_flow(hostel, start=start, end=end, branch=branch)

    def _acct_total(subtypes, type_):
        total = ZERO
        for acc in Account.objects.filter(
            hostel=hostel, is_group=False, type=type_, subtype__in=subtypes
        ):
            bal = account_balance(hostel, acc, as_of=as_of, branch=branch)
            total += bal if type_ == AccountType.ASSET else -bal
        return total.quantize(ZERO)

    cash_bank = _acct_total(["cash", "bank"], AccountType.ASSET)
    receivable = _acct_total(["receivable"], AccountType.ASSET)
    payable = _acct_total(["payable"], AccountType.LIABILITY)

    total_assets = Decimal(bs["total_assets"])
    total_liabilities = Decimal(bs["total_liabilities"])
    # Current ratio & working capital use current buckets as an approximation.
    current_ratio = (
        str((total_assets / total_liabilities).quantize(Decimal("0.01")))
        if total_liabilities > 0 else None
    )

    return {
        "as_of": as_of,
        "period": {"start": start, "end": end},
        "totals": {
            "total_assets": bs["total_assets"],
            "total_liabilities": bs["total_liabilities"],
            "total_equity": bs["total_equity"],
            "net_income": pl["net_profit"],
            "revenue": pl["total_income"],
            "expenses": pl["total_expenses"],
            "cash_bank": str(cash_bank),
            "accounts_receivable": str(receivable),
            "accounts_payable": str(payable),
            "ending_cash": cf["ending_cash"],
            "working_capital": str((total_assets - total_liabilities).quantize(ZERO)),
            "current_ratio": current_ratio,
        },
        "balance_sheet_balanced": bs["balanced"],
    }


# --------------------------------------------------------------------------- #
# Statement of changes in equity
# --------------------------------------------------------------------------- #
def statement_of_equity(hostel, *, start, end, branch=None):
    """Movement in each equity account over [start, end]: opening balance
    (credit-positive, as of the day before ``start``), the period's net
    movement, and the closing balance. The period's unclosed net income is
    surfaced as a synthetic "Current Year Earnings" component so the closing
    total ties to the balance sheet."""
    equity_accounts = list(
        Account.objects.filter(
            hostel=hostel, is_group=False, type=AccountType.EQUITY
        ).only("id", "code", "name", "subtype").order_by("code")
    )
    day_before = _day_before(start)
    components = []
    opening_total = ZERO
    closing_total = ZERO
    for account in equity_accounts:
        opening = -account_balance(hostel, account, as_of=day_before, branch=branch)  # credit-positive
        closing = -account_balance(hostel, account, as_of=end, branch=branch)
        movement = (closing - opening).quantize(ZERO)
        if opening == 0 and closing == 0 and movement == 0:
            continue
        opening_total += opening
        closing_total += closing
        components.append({
            "account_id": str(account.id),
            "code": account.code,
            "name": account.name,
            "opening": str(opening.quantize(ZERO)),
            "movement": str(movement),
            "closing": str(closing.quantize(ZERO)),
        })

    # Unclosed P&L for the period flows into equity as Current Year Earnings.
    pl = profit_and_loss(hostel, start=start, end=end, branch=branch)
    net_income = Decimal(pl["net_profit"])
    if net_income != 0:
        components.append({
            "account_id": None,
            "code": "3300",
            "name": "Current Year Earnings",
            "opening": str(ZERO.quantize(ZERO)),
            "movement": str(net_income.quantize(ZERO)),
            "closing": str(net_income.quantize(ZERO)),
        })
        closing_total += net_income

    return {
        "start": start,
        "end": end,
        "components": components,
        "opening_equity": str(opening_total.quantize(ZERO)),
        "net_income": str(net_income.quantize(ZERO)),
        "movement": str((closing_total - opening_total).quantize(ZERO)),
        "closing_equity": str(closing_total.quantize(ZERO)),
    }


# --------------------------------------------------------------------------- #
# Monthly trends (dashboard analytics)
# --------------------------------------------------------------------------- #
def _month_starts(end, months):
    """The first-of-month dates for the ``months`` window ending in ``end``'s
    month, oldest first — e.g. [2025-02-01, …, 2026-01-01]."""
    year, month = end.year, end.month
    seq = []
    for _ in range(months):
        seq.append((year, month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    seq.reverse()
    from datetime import date as _date

    return [_date(y, m, 1) for (y, m) in seq]


def monthly_trends(hostel, *, end, months=12, branch=None):
    """Per-month revenue, expenses, profit and cash movement over the trailing
    ``months`` window — the series behind the dashboard trend charts. Derived
    from posted ledger rows in two grouped queries (income/expense, then cash)."""
    starts = _month_starts(end, months)
    window_start = starts[0]

    # Income & expense grouped by month and account type.
    pl_rows = (
        _base_qs(hostel, branch=branch)
        .filter(date__gte=window_start, date__lte=end)
        .filter(account__type__in=[AccountType.INCOME, AccountType.EXPENSE])
        .annotate(m=TruncMonth("date"))
        .values("m", "account__type")
        .annotate(
            d=Coalesce(Sum("debit"), Value(ZERO, output_field=_MONEY)),
            c=Coalesce(Sum("credit"), Value(ZERO, output_field=_MONEY)),
        )
    )
    # Cash & bank movement grouped by month.
    cash_ids = list(
        Account.objects.filter(
            hostel=hostel, is_group=False, type=AccountType.ASSET,
            subtype__in=["cash", "bank"],
        ).values_list("id", flat=True)
    )
    cash_rows = (
        _base_qs(hostel, branch=branch)
        .filter(date__gte=window_start, date__lte=end, account_id__in=cash_ids)
        .annotate(m=TruncMonth("date"))
        .values("m")
        .annotate(
            d=Coalesce(Sum("debit"), Value(ZERO, output_field=_MONEY)),
            c=Coalesce(Sum("credit"), Value(ZERO, output_field=_MONEY)),
        )
    )

    revenue = {s: ZERO for s in starts}
    expenses = {s: ZERO for s in starts}
    cash_in = {s: ZERO for s in starts}
    cash_out = {s: ZERO for s in starts}
    for r in pl_rows:
        key = r["m"] if not hasattr(r["m"], "date") else r["m"].date()
        if key not in revenue:
            continue
        if r["account__type"] == AccountType.INCOME:
            revenue[key] += r["c"] - r["d"]
        else:
            expenses[key] += r["d"] - r["c"]
    for r in cash_rows:
        key = r["m"] if not hasattr(r["m"], "date") else r["m"].date()
        if key not in cash_in:
            continue
        cash_in[key] += r["d"]
        cash_out[key] += r["c"]

    series = []
    for s in starts:
        rev = revenue[s].quantize(ZERO)
        exp = expenses[s].quantize(ZERO)
        cin = cash_in[s].quantize(ZERO)
        cout = cash_out[s].quantize(ZERO)
        series.append({
            "month": s.strftime("%Y-%m"),
            "label": s.strftime("%b %Y"),
            "revenue": str(rev),
            "expenses": str(exp),
            "profit": str((rev - exp).quantize(ZERO)),
            "cash_in": str(cin),
            "cash_out": str(cout),
            "net_cash": str((cin - cout).quantize(ZERO)),
        })
    return {"start": window_start, "end": end, "months": months, "series": series}
