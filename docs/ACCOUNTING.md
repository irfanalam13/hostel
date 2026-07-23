# Accounting & Bookkeeping Module

Enterprise double-entry accounting for a hostel workspace, modeled on ERP
accounting cores (NetSuite / Business Central / Odoo) but scoped to a tenant.
Provides a configurable chart of accounts, balanced journal entries with an
approval workflow, an immutable general ledger, statutory financial statements
(trial balance, P&L, balance sheet, cash flow), fiscal-year/period management
with locking, fixed assets & depreciation, budgets, tax codes, cost centers,
multi-branch and multi-currency scaffolding, and bank reconciliation.

It is the formal accounting tier layered **on top of** the operational
`apps.finance` module (which handles invoices/payments/expenses via a simple
`LedgerTransaction` feed). `apps.finance` answers "who owes what and what did we
collect"; `apps.accounting` answers "what do the books say" in GAAP/IFRS-shaped
double-entry.

- **Backend:** `backend/apps/accounting/` → `/api/accounting/`
- **Frontend:** `frontend/apps/admin/src/features/accounting/` → `/accounting`

Same platform rails as every other module: 100% tenant isolation
(`HostelScopedModel` + `request.hostel` scoping), enterprise RBAC
(`accounting.*`), plan gating (`RequiresFeature("accounting")` — the feature is
**default-disabled** in the subscriptions catalog, so accounting is an
upgrade-tier capability), and async audit logging on every mutation.

---

## 1. The invariant: the books always balance

Money only enters the ledger through a **posted** `JournalEntry` whose debit and
credit lines are equal. The engine (`services.validate_lines` + `post_journal`)
refuses to post anything unbalanced, one-sided-and-both-columns, into a group
account, or into a closed period. Because every posting is balanced by
construction, every statement derived from the ledger balances too:

- **Trial balance** — total debits equal total credits.
- **Balance sheet** — Assets = Liabilities + Equity (unclosed P&L folds into
  equity as *Current Year Earnings*).

Posted entries are **immutable**. Corrections are made with a reversing entry
(`reverse_journal`), never an edit — the original flips to `reversed` and a
mirror journal nets it to zero.

Account balances are computed **purely from posted `LedgerEntry` rows**
(signed, debit-positive: `balance = Σdebit − Σcredit`). Opening balances are
themselves posted as a balanced opening journal
(`services.post_opening_balances`, routing any net difference to *Opening
Balance Equity*), so nothing can silently unbalance the books.

---

## 2. Data model (`apps/accounting/models.py`)

| Area | Models |
|---|---|
| Numbering | `NumberSequence` (row-locked journal voucher numbers) |
| Dimensions | `Branch`, `CostCenter`, `Currency`, `ExchangeRate` |
| Calendar | `FiscalYear`, `AccountingPeriod` (period locking) |
| Chart | `Account` (tree via `parent`, `type`, `is_group`, `normal_balance`), `TaxCode` |
| Journals | `JournalEntry` (workflow + reversal linkage), `JournalLine` |
| Ledger | `LedgerEntry` (immutable posted movements) |
| Budgeting | `Budget`, `BudgetLine` |
| Assets | `FixedAsset`, `DepreciationEntry` |
| Banking | `BankAccount`, `BankStatementLine` |

Account types are `asset / liability / equity / income / expense`; asset &
expense are debit-normal, the rest credit-normal. A standard hostel chart of
accounts is seeded per workspace on first use (`coa.py`,
`services.ensure_chart_of_accounts`), with anchor accounts the engine posts to
automatically: **Retained Earnings (3200)**, **Current Year Earnings (3300)**,
**Opening Balance Equity (3900)**, **Accumulated Depreciation (1590)**,
**Depreciation Expense (5190)**.

---

## 3. Journal lifecycle

```
draft → submitted → approved → posted → (reversed)
```

`draft/submitted/approved` are editable; **posting** writes one immutable
`LedgerEntry` per line, stamps the period, locks the entry and freezes it.
Each transition is a distinct RBAC verb (see §5), enabling a separation-of-duties
approval workflow (an accountant submits, a finance manager approves & posts).

`services.py` owns every ledger-touching operation, all inside DB transactions:
`create_journal`, `replace_lines`, `submit/approve/post_journal`,
`reverse_journal`, `post_opening_balances`, `close_period`/`reopen_period`,
`close_fiscal_year` (posts a closing journal moving income/expense into Retained
Earnings, then locks the year), and `run_depreciation` (straight-line or
declining-balance, posting Dr depreciation expense / Cr accumulated depreciation).

---

## 4. Statements (`apps/accounting/statements.py`)

Pure functions over posted ledger rows, one query per statement:
`trial_balance` (as-of), `profit_and_loss` (range), `balance_sheet` (as-of, with
net income folded into equity), `cash_flow` (movement on cash & bank accounts),
`general_ledger` (running balance for one account), and `dashboard_snapshot`
(the KPI bundle). All figures are quantized decimal strings so the wire format
is stable across databases.

---

## 5. RBAC

`accounting` is a first-class module in `apps.common.rbac`:

- CRUD: `accounting.view / create / edit / delete`
- Verbs: `accounting.post` (post journals / depreciation / opening balances),
  `accounting.approve` (approve journals & budgets), `accounting.reconcile`
  (bank reconciliation), `accounting.close` (close periods & fiscal years),
  `accounting.export`.

Default grants: OWNER/ADMIN `*`; MANAGER & ACCOUNTANT `accounting.*`. WARDEN and
below have none. The seeded "Manager"/"Accountant" staff system roles also carry
`accounting.*`, and per-tenant custom roles pick the new permissions up
automatically. Every viewset uses
`[IsHostelResolved, ActionPermissions, RequiresFeature("accounting")]` with a
per-action `permission_map`.

---

## 6. API surface (`/api/accounting/`)

CRUD: `accounts/` (+`seed-defaults/`, `{id}/ledger/`), `journals/`
(+`submit|approve|post|reverse`), `ledger/` (read-only), `fiscal-years/`
(+`generate-periods|post-opening-balances|close`), `periods/` (+`close|reopen`),
`tax-codes/`, `cost-centers/`, `branches/`, `currencies/`, `exchange-rates/`,
`budgets/` (+`approve`), `fixed-assets/` (+`depreciate|dispose|depreciations`),
`bank-accounts/`, `bank-statement-lines/` (+`reconcile|unreconcile`).

Statements: `reports/{trial-balance, profit-loss, balance-sheet, cash-flow,
journal-register, export}` and `dashboard/summary/`. Responses use the standard
`{success, message, data, meta}` envelope.

---

## 7. Tests

`backend/apps/accounting/tests/` (38 tests, all green):

- `test_engine.py` — balanced posting, group-account rejection, immutability,
  reversal-nets-to-zero, period locking, opening balances, year-end close moving
  P&L to retained earnings, straight-line depreciation.
- `test_statements.py` — trial balance balances, P&L net profit, the accounting
  equation on the balance sheet, cash-flow ending cash, running-balance GL.
- `test_api.py` (+ `conftest.py` enabling the plan feature) — end-to-end through
  the auth + tenant + RBAC stack, plus cross-tenant isolation (another
  workspace's journals/ledger are invisible and unreferenceable) and per-role
  permission enforcement.

Run: `cd backend && pytest apps/accounting/`.
