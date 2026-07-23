"""The accounting engine: journal lifecycle, the posting engine, reversals,
period/fiscal-year close, opening balances and depreciation.

Every mutation that touches the ledger runs inside a DB transaction and upholds
the module's invariant — a journal only posts when its debits equal its credits
and its target period is open, so the ledger is always balanced and never
written into a locked period.
"""
import csv
import io
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .coa import (
    OPENING_BALANCE_EQUITY_CODE,
    RETAINED_EARNINGS_CODE,
    seed_default_accounts,
)
from .models import (
    Account,
    AccountingPeriod,
    AccountType,
    BankAccount,
    BankStatementLine,
    DepreciationEntry,
    FiscalYear,
    FixedAsset,
    JournalEntry,
    JournalLine,
    LedgerEntry,
    NumberSequence,
)

TWO = Decimal("0.01")
ZERO = Decimal("0.00")


# --------------------------------------------------------------------------- #
# Numbering & setup
# --------------------------------------------------------------------------- #
def next_journal_number(hostel) -> str:
    seq, _ = NumberSequence.objects.get_or_create(hostel=hostel, key="journal")
    seq = NumberSequence.objects.select_for_update().get(pk=seq.pk)
    number = seq.next_number
    seq.next_number = number + 1
    seq.save(update_fields=["next_number", "updated_at"])
    return f"JV-{number:06d}"


def ensure_chart_of_accounts(hostel) -> None:
    """Seed the default CoA on first use (idempotent)."""
    if not Account.objects.filter(hostel=hostel).exists():
        seed_default_accounts(hostel)


def get_anchor_account(hostel, code: str):
    ensure_chart_of_accounts(hostel)
    return Account.objects.filter(hostel=hostel, code=code).first()


# --------------------------------------------------------------------------- #
# Period resolution & locking
# --------------------------------------------------------------------------- #
def resolve_period(hostel, on_date):
    """The accounting period a date falls in, or None when no fiscal calendar
    covers it (posting is then unrestricted — a workspace need not run periods)."""
    return (
        AccountingPeriod.objects.filter(
            hostel=hostel, start_date__lte=on_date, end_date__gte=on_date
        )
        .select_related("fiscal_year")
        .first()
    )


def assert_period_open(hostel, on_date) -> None:
    period = resolve_period(hostel, on_date)
    if period is None:
        return
    if period.is_closed or period.fiscal_year.is_closed:
        raise ValidationError(
            {"detail": f"Accounting period {period.name} is closed — postings are locked."}
        )


# --------------------------------------------------------------------------- #
# Journal build & lifecycle
# --------------------------------------------------------------------------- #
def _line_totals(lines):
    debit = sum((Decimal(str(x.get("debit") or 0)) for x in lines), ZERO)
    credit = sum((Decimal(str(x.get("credit") or 0)) for x in lines), ZERO)
    return debit.quantize(TWO), credit.quantize(TWO)


def validate_lines(lines):
    """A well-formed journal has ≥2 lines, every line one-sided and non-negative,
    and equal debit/credit totals > 0."""
    if not lines or len(lines) < 2:
        raise ValidationError({"lines": "A journal needs at least two lines."})
    for line in lines:
        debit = Decimal(str(line.get("debit") or 0))
        credit = Decimal(str(line.get("credit") or 0))
        if debit < 0 or credit < 0:
            raise ValidationError({"lines": "Amounts cannot be negative."})
        if debit > 0 and credit > 0:
            raise ValidationError({"lines": "A line cannot be both debit and credit."})
        if debit == 0 and credit == 0:
            raise ValidationError({"lines": "Each line must carry a debit or a credit."})
    debit, credit = _line_totals(lines)
    if debit != credit:
        raise ValidationError(
            {"lines": f"Journal is out of balance: debit {debit} ≠ credit {credit}."}
        )
    if debit == 0:
        raise ValidationError({"lines": "A journal must move a non-zero amount."})
    return debit, credit


@transaction.atomic
def create_journal(*, hostel, actor, lines, status=None, **fields):
    """Build a draft (or posted) journal with its lines. ``lines`` are dicts of
    ``account / debit / credit / description / cost_center / branch``."""
    debit, credit = validate_lines(lines)
    target_status = status or JournalEntry.Status.DRAFT

    journal = JournalEntry.objects.create(
        hostel=hostel,
        number=next_journal_number(hostel),
        status=JournalEntry.Status.DRAFT,
        total_debit=debit,
        total_credit=credit,
        created_by=actor,
        **fields,
    )
    for line in lines:
        JournalLine.objects.create(
            hostel=hostel,
            journal=journal,
            account=line["account"],
            debit=Decimal(str(line.get("debit") or 0)).quantize(TWO),
            credit=Decimal(str(line.get("credit") or 0)).quantize(TWO),
            description=line.get("description", ""),
            cost_center=line.get("cost_center"),
            branch=line.get("branch"),
        )
    # Optionally fast-forward through the workflow (e.g. auto-posted system
    # journals). Manual journals stay draft for the approval workflow.
    if target_status == JournalEntry.Status.POSTED:
        post_journal(journal, actor=actor)
    elif target_status != JournalEntry.Status.DRAFT:
        journal.status = target_status
        journal.save(update_fields=["status", "updated_at"])
    return journal


def _recompute_totals(journal):
    agg = journal.lines.aggregate(d=Sum("debit"), c=Sum("credit"))
    journal.total_debit = (agg["d"] or ZERO).quantize(TWO)
    journal.total_credit = (agg["c"] or ZERO).quantize(TWO)
    journal.save(update_fields=["total_debit", "total_credit", "updated_at"])


def _guard_mutable(journal):
    if journal.status in (JournalEntry.Status.POSTED, JournalEntry.Status.REVERSED):
        raise ValidationError({"detail": "Posted journals are immutable — reverse instead."})


@transaction.atomic
def replace_lines(journal, lines):
    """Swap a draft/submitted journal's lines (validates balance)."""
    _guard_mutable(journal)
    validate_lines(lines)
    journal.lines.all().delete()
    for line in lines:
        JournalLine.objects.create(
            hostel=journal.hostel,
            journal=journal,
            account=line["account"],
            debit=Decimal(str(line.get("debit") or 0)).quantize(TWO),
            credit=Decimal(str(line.get("credit") or 0)).quantize(TWO),
            description=line.get("description", ""),
            cost_center=line.get("cost_center"),
            branch=line.get("branch"),
        )
    _recompute_totals(journal)
    return journal


def submit_journal(journal, *, actor):
    _guard_mutable(journal)
    validate_lines(list(journal.lines.values("debit", "credit", "account")))
    journal.status = JournalEntry.Status.SUBMITTED
    journal.submitted_by = actor
    journal.save(update_fields=["status", "submitted_by", "updated_at"])
    return journal


def approve_journal(journal, *, actor):
    if journal.status not in (JournalEntry.Status.SUBMITTED, JournalEntry.Status.DRAFT):
        raise ValidationError({"detail": "Only draft or submitted journals can be approved."})
    journal.status = JournalEntry.Status.APPROVED
    journal.approved_by = actor
    journal.save(update_fields=["status", "approved_by", "updated_at"])
    return journal


@transaction.atomic
def post_journal(journal, *, actor):
    """Post an approved/draft journal to the ledger. Re-validates balance,
    enforces period locking, forbids posting to group accounts, then writes an
    immutable ``LedgerEntry`` per line and freezes the journal."""
    if journal.status == JournalEntry.Status.POSTED:
        return journal
    if journal.status == JournalEntry.Status.REVERSED:
        raise ValidationError({"detail": "Reversed journals cannot be reposted."})

    lines = list(journal.lines.select_related("account"))
    validate_lines([{"debit": x.debit, "credit": x.credit} for x in lines])

    posting_date = journal.posting_date or journal.date
    assert_period_open(journal.hostel, posting_date)

    for line in lines:
        if line.account.is_group:
            raise ValidationError(
                {"detail": f"Account {line.account.code} is a group account and cannot be posted to."}
            )
        if not line.account.is_active:
            raise ValidationError({"detail": f"Account {line.account.code} is inactive."})

    LedgerEntry.objects.bulk_create([
        LedgerEntry(
            hostel=journal.hostel,
            account=line.account,
            journal=journal,
            journal_line=line,
            date=posting_date,
            debit=line.debit,
            credit=line.credit,
            description=line.description or journal.description,
            cost_center=line.cost_center,
            branch=line.branch or journal.branch,
        )
        for line in lines
    ])

    journal.status = JournalEntry.Status.POSTED
    journal.posting_date = posting_date
    journal.posted_by = actor
    journal.posted_at = timezone.now()
    journal.is_locked = True
    if journal.period_id is None:
        journal.period = resolve_period(journal.hostel, posting_date)
    _recompute_totals(journal)
    journal.save(
        update_fields=[
            "status", "posting_date", "posted_by", "posted_at", "is_locked",
            "period", "updated_at",
        ]
    )
    return journal


@transaction.atomic
def reverse_journal(journal, *, actor, date=None, description=""):
    """Create and post a mirror journal that negates a posted one. The original
    is marked reversed; the ledger nets to zero for the pair."""
    if journal.status != JournalEntry.Status.POSTED:
        raise ValidationError({"detail": "Only posted journals can be reversed."})
    if journal.reversed_by_entries.exists():
        raise ValidationError({"detail": "This journal has already been reversed."})

    reversal_date = date or timezone.localdate()
    assert_period_open(journal.hostel, reversal_date)

    lines = [
        {
            "account": line.account,
            "debit": line.credit,   # swap sides
            "credit": line.debit,
            "description": f"Reversal: {line.description}".strip(": "),
            "cost_center": line.cost_center,
            "branch": line.branch,
        }
        for line in journal.lines.select_related("account")
    ]
    reversal = create_journal(
        hostel=journal.hostel,
        actor=actor,
        lines=lines,
        status=JournalEntry.Status.POSTED,
        date=reversal_date,
        journal_type=JournalEntry.JournalType.REVERSAL,
        description=description or f"Reversal of {journal.number}",
        reference=journal.number,
        reverses=journal,
        branch=journal.branch,
    )
    journal.status = JournalEntry.Status.REVERSED
    journal.save(update_fields=["status", "updated_at"])
    return reversal


# --------------------------------------------------------------------------- #
# Opening balances
# --------------------------------------------------------------------------- #
@transaction.atomic
def post_opening_balances(*, hostel, actor, fiscal_year: FiscalYear):
    """Post a single balanced opening journal from every account's
    ``opening_balance`` field, routing the net difference to Opening Balance
    Equity so the entry always balances."""
    ensure_chart_of_accounts(hostel)
    obe = get_anchor_account(hostel, OPENING_BALANCE_EQUITY_CODE)
    if obe is None:
        raise ValidationError({"detail": "Opening Balance Equity account is missing."})

    lines = []
    net = ZERO  # signed debit-positive sum of account opening balances
    for account in Account.objects.filter(hostel=hostel, is_group=False).exclude(
        opening_balance=0
    ).exclude(id=obe.id):
        signed = Decimal(account.opening_balance)
        net += signed
        if signed >= 0:
            lines.append({"account": account, "debit": signed, "credit": ZERO,
                          "description": "Opening balance"})
        else:
            lines.append({"account": account, "debit": ZERO, "credit": -signed,
                          "description": "Opening balance"})
    if not lines:
        raise ValidationError({"detail": "No account opening balances to post."})

    # Balance to Opening Balance Equity.
    if net > 0:
        lines.append({"account": obe, "debit": ZERO, "credit": net, "description": "Opening balance"})
    elif net < 0:
        lines.append({"account": obe, "debit": -net, "credit": ZERO, "description": "Opening balance"})

    return create_journal(
        hostel=hostel, actor=actor, lines=lines,
        status=JournalEntry.Status.POSTED,
        date=fiscal_year.start_date,
        journal_type=JournalEntry.JournalType.OPENING,
        description=f"Opening balances — {fiscal_year.name}",
    )


# --------------------------------------------------------------------------- #
# Period / fiscal-year close
# --------------------------------------------------------------------------- #
def close_period(period: AccountingPeriod):
    period.is_closed = True
    period.closed_at = timezone.now()
    period.save(update_fields=["is_closed", "closed_at", "updated_at"])
    return period


def reopen_period(period: AccountingPeriod):
    if period.fiscal_year.is_closed:
        raise ValidationError({"detail": "Reopen the fiscal year before its periods."})
    period.is_closed = False
    period.closed_at = None
    period.save(update_fields=["is_closed", "closed_at", "updated_at"])
    return period


@transaction.atomic
def close_fiscal_year(*, hostel, actor, fiscal_year: FiscalYear):
    """Post a closing journal that zeroes every income/expense account into
    Retained Earnings, then lock the year and its periods."""
    if fiscal_year.is_closed:
        raise ValidationError({"detail": "This fiscal year is already closed."})
    retained = get_anchor_account(hostel, RETAINED_EARNINGS_CODE)
    if retained is None:
        raise ValidationError({"detail": "Retained Earnings account is missing."})

    from .statements import account_activity  # local import avoids a cycle

    lines = []
    net_income = ZERO  # credit-positive P&L result
    for account in Account.objects.filter(
        hostel=hostel, is_group=False, type__in=[AccountType.INCOME, AccountType.EXPENSE]
    ):
        debit, credit = account_activity(
            hostel, account, fiscal_year.start_date, fiscal_year.end_date
        )
        balance = credit - debit  # income positive, expense negative
        if balance == 0:
            continue
        net_income += balance
        # Zero the account: post the opposite side.
        if balance > 0:  # income credit balance → debit to clear
            lines.append({"account": account, "debit": balance, "credit": ZERO,
                          "description": "Year-end close"})
        else:  # expense debit balance → credit to clear
            lines.append({"account": account, "debit": ZERO, "credit": -balance,
                          "description": "Year-end close"})

    if lines:
        # Balance the net result to Retained Earnings.
        if net_income > 0:
            lines.append({"account": retained, "debit": ZERO, "credit": net_income,
                          "description": "Net income to retained earnings"})
        else:
            lines.append({"account": retained, "debit": -net_income, "credit": ZERO,
                          "description": "Net loss to retained earnings"})
        create_journal(
            hostel=hostel, actor=actor, lines=lines,
            status=JournalEntry.Status.POSTED,
            date=fiscal_year.end_date,
            journal_type=JournalEntry.JournalType.CLOSING,
            description=f"Year-end closing — {fiscal_year.name}",
        )

    fiscal_year.periods.update(is_closed=True, closed_at=timezone.now())
    fiscal_year.is_closed = True
    fiscal_year.closed_at = timezone.now()
    fiscal_year.closed_by = actor
    fiscal_year.save(update_fields=["is_closed", "closed_at", "closed_by", "updated_at"])
    return fiscal_year


# --------------------------------------------------------------------------- #
# Depreciation
# --------------------------------------------------------------------------- #
def _period_depreciation(asset: FixedAsset) -> Decimal:
    """The depreciation amount for one period (month), capped so accumulated
    never exceeds the depreciable base."""
    if asset.depreciation_method == FixedAsset.DepreciationMethod.NONE:
        return ZERO
    remaining = asset.depreciable_base - asset.accumulated_depreciation
    if remaining <= 0:
        return ZERO
    if asset.depreciation_method == FixedAsset.DepreciationMethod.STRAIGHT_LINE:
        months = asset.useful_life_months or 1
        amount = (asset.depreciable_base / Decimal(months)).quantize(TWO)
    else:  # declining balance on net book value
        rate = asset.declining_rate / Decimal("100")
        monthly = rate / Decimal("12")
        amount = (asset.net_book_value * monthly).quantize(TWO)
    return min(amount, remaining)


@transaction.atomic
def run_depreciation(*, hostel, actor, asset: FixedAsset, on_date=None):
    """Post one period of depreciation for an asset: Dr depreciation expense,
    Cr accumulated depreciation, and record the ``DepreciationEntry``."""
    on_date = on_date or timezone.localdate()
    amount = _period_depreciation(asset)
    if amount <= 0:
        raise ValidationError({"detail": "Asset is fully depreciated or non-depreciating."})

    expense = asset.depreciation_expense_account or get_anchor_account(hostel, "5190")
    accumulated = asset.accumulated_depreciation_account or get_anchor_account(hostel, "1590")
    if expense is None or accumulated is None:
        raise ValidationError({"detail": "Depreciation accounts are not configured."})

    journal = create_journal(
        hostel=hostel, actor=actor,
        lines=[
            {"account": expense, "debit": amount, "credit": ZERO,
             "description": f"Depreciation — {asset.name}"},
            {"account": accumulated, "debit": ZERO, "credit": amount,
             "description": f"Depreciation — {asset.name}"},
        ],
        status=JournalEntry.Status.POSTED,
        date=on_date,
        journal_type=JournalEntry.JournalType.DEPRECIATION,
        description=f"Depreciation — {asset.name}",
        branch=asset.branch,
    )
    asset.accumulated_depreciation += amount
    if asset.accumulated_depreciation >= asset.depreciable_base:
        asset.status = FixedAsset.Status.FULLY_DEPRECIATED
    asset.save(update_fields=["accumulated_depreciation", "status", "updated_at"])
    DepreciationEntry.objects.create(
        hostel=hostel, asset=asset, date=on_date, amount=amount, journal=journal
    )
    return journal


# --------------------------------------------------------------------------- #
# Budget variance (planned vs actual)
# --------------------------------------------------------------------------- #
def budget_variance(*, hostel, budget):
    """Compare a budget's planned figures against actual ledger activity over
    its fiscal year. Variance is reported *favourable-positive*: for income,
    beating the plan is positive; for expenses, spending under the plan is
    positive."""
    from .statements import account_activity  # local import avoids a cycle

    fy = budget.fiscal_year
    per_account = defaultdict(lambda: ZERO)
    accounts = {}
    for line in budget.lines.select_related("account"):
        per_account[line.account_id] += line.amount
        accounts[line.account_id] = line.account

    rows = []
    total_budget = ZERO
    total_actual = ZERO
    total_variance = ZERO
    for acc_id, budgeted in per_account.items():
        account = accounts[acc_id]
        debit, credit = account_activity(
            hostel, account, fy.start_date, fy.end_date,
            branch=budget.branch, cost_center=budget.cost_center,
        )
        if account.type == AccountType.INCOME:
            actual = (credit - debit).quantize(TWO)
            variance = (actual - budgeted).quantize(TWO)
        else:
            actual = (debit - credit).quantize(TWO)
            variance = (budgeted - actual).quantize(TWO)
        utilization = (
            (actual / budgeted * Decimal("100")).quantize(TWO) if budgeted else None
        )
        total_budget += budgeted
        total_actual += actual
        total_variance += variance
        rows.append({
            "account_id": str(acc_id),
            "code": account.code,
            "name": account.name,
            "type": account.type,
            "budget": str(budgeted.quantize(TWO)),
            "actual": str(actual),
            "variance": str(variance),
            "utilization": str(utilization) if utilization is not None else None,
        })
    rows.sort(key=lambda r: r["code"])
    return {
        "budget_id": str(budget.id),
        "name": budget.name,
        "fiscal_year": fy.name,
        "rows": rows,
        "total_budget": str(total_budget.quantize(TWO)),
        "total_actual": str(total_actual.quantize(TWO)),
        "total_variance": str(total_variance.quantize(TWO)),
    }


# --------------------------------------------------------------------------- #
# Bank statement import & auto-matching
# --------------------------------------------------------------------------- #
def _parse_amount(raw):
    if raw is None:
        raise InvalidOperation("empty")
    cleaned = str(raw).strip().replace(",", "").replace("(", "-").replace(")", "")
    return Decimal(cleaned).quantize(TWO)


def _parse_row_date(raw):
    text = str(raw).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            from datetime import datetime

            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    # Last resort: ISO parse.
    return date.fromisoformat(text)


@transaction.atomic
def import_bank_statement(*, hostel, bank_account: BankAccount, csv_text: str):
    """Bulk-create statement lines from CSV text. Accepts a header row with any
    of ``date/description/reference/amount`` (case-insensitive) or bare
    positional columns ``date, description, reference, amount``. Signed amounts:
    positive = money in, negative = money out."""
    reader = csv.reader(io.StringIO(csv_text.strip()))
    records = [r for r in reader if any(cell.strip() for cell in r)]
    if not records:
        raise ValidationError({"detail": "The statement file is empty."})

    header = [c.strip().lower() for c in records[0]]
    known = {"date", "description", "reference", "amount", "ref", "memo", "narration"}
    has_header = any(c in known for c in header)
    if has_header:
        def col(*names):
            for n in names:
                if n in header:
                    return header.index(n)
            return None

        idx_date = col("date")
        idx_desc = col("description", "memo", "narration")
        idx_ref = col("reference", "ref")
        idx_amt = col("amount")
        body = records[1:]
    else:
        idx_date, idx_desc, idx_ref, idx_amt = 0, 1, 2, 3
        body = records

    if idx_date is None or idx_amt is None:
        raise ValidationError({"detail": "CSV must have at least date and amount columns."})

    created = []
    for i, row in enumerate(body, start=2):
        def cell(idx):
            return row[idx].strip() if idx is not None and idx < len(row) else ""

        try:
            line_date = _parse_row_date(cell(idx_date))
            amount = _parse_amount(cell(idx_amt))
        except (InvalidOperation, ValueError) as exc:
            raise ValidationError({"detail": f"Row {i}: invalid date or amount."}) from exc
        created.append(BankStatementLine(
            hostel=hostel, bank_account=bank_account, date=line_date,
            description=cell(idx_desc), reference=cell(idx_ref), amount=amount,
        ))
    if not created:
        raise ValidationError({"detail": "No statement rows found."})
    BankStatementLine.objects.bulk_create(created)
    return created


@transaction.atomic
def auto_match_bank_account(*, hostel, bank_account: BankAccount, tolerance_days: int = 4):
    """Match unreconciled statement lines against posted ledger movements on the
    bank's GL account: a positive statement amount matches a debit of the same
    size, a negative amount a credit, within ``tolerance_days``. Each ledger
    line is consumed once. Returns the number of lines matched."""
    gl_account = bank_account.account
    # Ledger movements on the GL account not yet claimed by any statement line.
    claimed = set(
        BankStatementLine.objects.filter(
            hostel=hostel, bank_account=bank_account, matched_line__isnull=False
        ).values_list("matched_line_id", flat=True)
    )
    pool = [
        e for e in LedgerEntry.objects.filter(hostel=hostel, account=gl_account)
        .select_related("journal_line")
        if e.journal_line_id is not None and e.journal_line_id not in claimed
    ]

    matched = 0
    for line in BankStatementLine.objects.filter(
        hostel=hostel, bank_account=bank_account, is_reconciled=False
    ).order_by("date"):
        want_debit = line.amount > 0
        target = abs(line.amount)
        for entry in pool:
            side = entry.debit if want_debit else entry.credit
            if side != target:
                continue
            if abs((entry.date - line.date).days) > tolerance_days:
                continue
            line.matched_line = entry.journal_line
            line.is_reconciled = True
            line.reconciled_at = timezone.now()
            line.save(update_fields=["matched_line", "is_reconciled", "reconciled_at", "updated_at"])
            pool.remove(entry)
            matched += 1
            break
    return matched
