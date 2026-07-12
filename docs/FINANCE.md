# Finance Management Module

Enterprise, fully tenant-isolated financial system for every workspace: fee
structures, resident billing/invoicing, fee collection, expenses, income,
refunds, discounts, scholarships, a cash-flow ledger, budgets, dashboards,
reports and CSV exports.

Built **on top of** the canonical Track A billing domain (`apps.residents`,
`apps.billing`) rather than replacing it. `apps.billing` keeps the simple
month-by-month `MonthlyDue`/`Payment` flow; `apps.finance` is the enterprise
accounting-friendly layer (documented numbering, tax, multi-line invoices,
approval workflows, an append-only ledger).

- **Backend:** `backend/apps/finance/` → `/api/finance/`
- **Frontend:** `frontend/apps/admin/src/features/finance/` → `/finance`

Same platform principles as the rest of the app: 100% multi-tenant isolation
(`HostelScopedModel` + `request.hostel` scoping everywhere), enterprise RBAC
(`finance.*`), plan/entitlement gating (`RequiresFeature("finance")`), async
audit logging, and idempotent payment writes (via the existing
`Idempotency-Key` middleware — no per-view code).

---

## 1. Data model

Everything is scoped to `tenants.Hostel` via `HostelScopedModel` (UUID pk +
timestamps + `hostel` FK). No financial row is ever shared across workspaces.

| Area | Models |
|---|---|
| Numbering | `DocumentSequence` (per-hostel invoice/receipt counters, row-locked) |
| Fees | `FeeCategory`, `FeeStructure`, `FeeAssignment` |
| Concessions | `Discount`, `Scholarship`, `ScholarshipAward` |
| Invoicing | `Invoice`, `InvoiceLine`, `InvoiceAdjustment` |
| Collection | `PaymentRecord` |
| Money out/in | `Expense` (+ `ExpenseCategory`), `Income`, `Refund` |
| Ledger | `LedgerTransaction` (append-only signed feed) |
| Budgeting | `Budget` |

**Amount invariants** mirror `apps.billing`: charges/payments are strictly
positive; computed rollups are non-negative. Signed values live *only* on
`LedgerTransaction` via its `direction` (`in`/`out`) flag.

**The ledger is the source of truth for reporting.** It is written *exclusively*
by the service layer when money actually settles — a payment verifies, an
expense is paid, income is recorded, or a refund processes. The dashboard,
cash-flow trend and all financial reports read from it.

> Scope note: this is an accounting-*friendly* ledger, not a full double-entry
> general ledger. `LedgerTransaction` is the append-only foundation; formal
> chart-of-accounts / journal-entries / trial-balance are a future layer on top
> of it.

---

## 2. Service layer owns the money math

`apps/finance/services.py` is the single place totals are computed and lifecycle
transitions happen, all inside DB transactions so concurrent collection can't
corrupt an invoice. Views only validate + authorize.

- `next_document_number(hostel, doc_type)` — mints `INV-000001` / `RCT-000001`
  under a `select_for_update` lock on the per-(hostel, type) counter.
- `create_invoice(...)` / `recalc_invoice(...)` — build lines + adjustments, then
  recompute `subtotal / tax_total / discount_total / scholarship_total / total /
  paid_amount` and derive status. **Invoice money fields are never written by API
  clients** — clients send quantities and rates; the server computes amounts.
- `settle_payment(...)` — verifies a payment, mints its receipt, posts the `in`
  ledger transaction, refreshes the invoice. Idempotent.
- `void_payment(...)` — cancels/fails a payment and backs a previously-verified
  one out of the ledger and its invoice.
- `process_refund(...)` — posts the `out` transaction and, when a payment is
  fully refunded, flips payment (and invoice) to refunded.
- `mark_expense_paid(...)` / `record_income_transaction(...)` — post ledger rows.

Only **verified** payments and **paid** expenses affect the ledger and invoice
rollups. Payments settle immediately by default; send `require_verification:true`
to park them as `pending` for a second approver (`finance.approve`).

---

## 3. RBAC

`finance` is a first-class module in `apps.common.rbac`:

- CRUD: `finance.view / create / edit / delete`
- Feature verbs: `finance.collect` (record payments), `finance.approve` (verify
  payments; approve expenses / refunds / scholarship awards), `finance.refund`
  (request & process refunds), `finance.export`.

Default grants: OWNER/ADMIN `*`; MANAGER & ACCOUNTANT `finance.*`; WARDEN
`finance.view`. The seeded "Manager" and "Accountant" staff system roles also
carry `finance.*`. Per-tenant custom roles pick up the new permissions
automatically via the staff role editor's catalog.

Every viewset uses `permission_classes = [IsHostelResolved, ActionPermissions,
RequiresFeature("finance")]` with a per-action `permission_map`.

---

## 4. Plan gating

The whole module sits behind the `finance` subscriptions feature
(`RequiresFeature("finance")`). The feature already exists in the catalog
(`apps/subscriptions/catalog.py`, default-enabled), so the Super Admin / plan
system can turn finance on or off per workspace with no code change. Blocked
requests return the structured `feature_not_available` 403 with upgrade context.

---

## 5. API surface (`/api/finance/`)

CRUD collections: `fee-categories/`, `fee-structures/`, `fee-assignments/`
(+`bulk-assign/`, `{id}/waive/`), `discounts/`, `scholarships/`,
`scholarship-awards/` (+`approve|reject|revoke`), `invoices/`
(+`issue|cancel`), `payments/` (+`verify|cancel|fail`), `expense-categories/`,
`expenses/` (+`approve|reject|mark-paid`), `income/`, `refunds/`
(+`approve|reject|process`), `budgets/`, `transactions/` (read-only ledger).

Analytics: `dashboard/summary/` (revenue/expense/profit/outstanding/collection
totals, invoice status counts, 12-month cash-flow trend, payment-method split,
upcoming dues, recent transactions) and `reports/{collections, profit-loss,
expense-breakdown, dues, export}` — `export/?type=…` streams CSV and is
`finance.export`-gated + audit-logged.

All lists support `?search=`, `?ordering=` and the documented filter params;
responses use the standard `{success, message, data, meta}` envelope.

---

## 6. Notifications & audit

Every mutation is audit-logged via `record_event` with `entity_type`
`finance.<model>`. Expense approval/rejection and refund approval/rejection/
completion fire an in-app/push notification to the requester (best-effort —
notification failures never break a finance write).

---

## 7. Tests

`backend/apps/finance/tests/`:

- `test_services.py` — document numbering, invoice math (tax, discounts, "never
  negative"), payment settle/void idempotency, refund flips, overdue, seeds.
- `test_api.py` — end-to-end flows through the full auth + tenant + RBAC stack,
  plus per-role permission enforcement.
- `test_isolation.py` — cross-tenant invisibility: another workspace's invoices,
  payments, ledger and dashboard totals are unreachable even with a valid
  session, and invoices can't reference another tenant's discounts/residents.

Run: `cd backend && pytest apps/finance/`.
