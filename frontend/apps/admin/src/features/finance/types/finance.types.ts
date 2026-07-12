/** Money values from the backend are decimal strings (e.g. "1250.00"). */
export type Money = string;

export type InvoiceStatus =
  | "draft"
  | "pending"
  | "partial"
  | "paid"
  | "overdue"
  | "cancelled"
  | "refunded";

export type PaymentStatus = "pending" | "verified" | "failed" | "cancelled" | "refunded";

export type PaymentMethod =
  | "cash"
  | "bank_transfer"
  | "mobile_banking"
  | "qr"
  | "card"
  | "online"
  | "upi"
  | "wallet"
  | "cheque"
  | "other";

export type Recurrence = "one_time" | "monthly" | "quarterly" | "semester" | "annual";

export type AdjustmentKind = "discount" | "scholarship" | "waiver";

/* ------------------------------- Dashboard ------------------------------- */

export type DashboardTotals = {
  total_revenue: Money;
  total_expenses: Money;
  net_profit: Money;
  outstanding_due: Money;
  total_collected: Money;
  todays_collection: Money;
  monthly_collection: Money;
  annual_revenue: Money;
  refund_total: Money;
  discount_total: Money;
  scholarship_total: Money;
  pending_payments: number;
  open_invoices: number;
  overdue_invoices: number;
};

export type CashFlowPoint = { month: string; in: Money; out: Money };

export type PaymentMethodStat = { method: PaymentMethod; total: Money; count: number };

export type UpcomingDue = {
  id: string;
  number: string;
  resident_name: string;
  due_date: string;
  balance: Money;
  status: InvoiceStatus;
};

export type FinanceDashboard = {
  totals: DashboardTotals;
  invoice_status_counts: Record<string, number>;
  cash_flow: CashFlowPoint[];
  payment_methods: PaymentMethodStat[];
  upcoming_dues: UpcomingDue[];
  recent_transactions: Transaction[];
};

/* -------------------------------- Invoices ------------------------------- */

export type InvoiceLine = {
  id: string;
  fee_structure: string | null;
  description: string;
  quantity: Money;
  unit_price: Money;
  tax_rate: Money;
  amount: Money;
  tax_amount: Money;
};

export type InvoiceAdjustment = {
  id: string;
  kind: AdjustmentKind;
  discount: string | null;
  scholarship_award: string | null;
  amount: Money;
  note: string;
};

export type InvoicePaymentRow = {
  id: string;
  receipt_number: string;
  amount: Money;
  method: PaymentMethod;
  status: PaymentStatus;
  reference: string;
  received_at: string;
};

export type Invoice = {
  id: string;
  number: string;
  resident: string;
  resident_name: string;
  status: InvoiceStatus;
  issue_date: string;
  due_date: string;
  currency: string;
  subtotal: Money;
  tax_total: Money;
  discount_total: Money;
  scholarship_total: Money;
  total: Money;
  paid_amount: Money;
  balance: Money;
  notes: string;
  terms: string;
  lines: InvoiceLine[];
  adjustments: InvoiceAdjustment[];
  payments: InvoicePaymentRow[];
  created_at: string;
};

export type CreateInvoiceLine = {
  description: string;
  fee_structure?: string;
  quantity?: string;
  unit_price: string;
  tax_rate?: string;
};

export type CreateInvoiceAdjustment = {
  kind: AdjustmentKind;
  discount?: string;
  scholarship_award?: string;
  amount?: string;
  note?: string;
};

export type CreateInvoicePayload = {
  resident: string;
  issue_date?: string;
  due_date?: string;
  currency?: string;
  notes?: string;
  terms?: string;
  as_draft?: boolean;
  lines: CreateInvoiceLine[];
  adjustments?: CreateInvoiceAdjustment[];
};

/* -------------------------------- Payments ------------------------------- */

export type Payment = {
  id: string;
  receipt_number: string;
  invoice: string | null;
  invoice_number: string | null;
  resident: string | null;
  resident_name: string | null;
  amount: Money;
  method: PaymentMethod;
  status: PaymentStatus;
  reference: string;
  note: string;
  received_at: string;
  verified_at: string | null;
};

export type CreatePaymentPayload = {
  invoice?: string;
  resident?: string;
  amount: string;
  method: PaymentMethod;
  reference?: string;
  note?: string;
  require_verification?: boolean;
};

/* ---------------------------------- Fees --------------------------------- */

export type FeeCategory = {
  id: string;
  name: string;
  code: string;
  description: string;
  is_system: boolean;
  is_active: boolean;
};

export type LateFineType = "none" | "fixed" | "percentage";

export type FeeStructure = {
  id: string;
  name: string;
  category: string;
  category_name: string;
  description: string;
  amount: Money;
  recurrence: Recurrence;
  tax_rate: Money;
  allow_installments: boolean;
  due_day: number;
  grace_period_days: number;
  late_fine_type: LateFineType;
  late_fine_amount: Money;
  is_active: boolean;
};

export type FeeAssignmentStatus = "active" | "paused" | "ended" | "waived";

export type FeeAssignment = {
  id: string;
  fee_structure: string;
  fee_name: string;
  resident: string;
  resident_name: string;
  amount_override: Money | null;
  effective_amount: Money;
  start_date: string;
  end_date: string | null;
  status: FeeAssignmentStatus;
  waived_reason: string;
};

export type BulkAssignPayload = {
  fee_structure: string;
  resident_ids: string[];
  amount_override?: string;
  start_date?: string;
};

/* ---------------------- Discounts & scholarships ------------------------- */

export type DiscountType = "percentage" | "fixed";
export type DiscountReason =
  | "seasonal"
  | "promotional"
  | "early_payment"
  | "sibling"
  | "merit"
  | "staff"
  | "custom";

export type Discount = {
  id: string;
  name: string;
  discount_type: DiscountType;
  value: Money;
  reason: DiscountReason;
  description: string;
  valid_from: string | null;
  valid_until: string | null;
  max_uses: number | null;
  used_count: number;
  is_active: boolean;
};

export type ScholarshipType =
  | "merit"
  | "need_based"
  | "sports"
  | "government"
  | "ngo"
  | "internal"
  | "custom";
export type AwardType = "percentage" | "fixed";

export type Scholarship = {
  id: string;
  name: string;
  scholarship_type: ScholarshipType;
  award_type: AwardType;
  value: Money;
  description: string;
  is_active: boolean;
  awards_count: number;
};

export type ScholarshipAwardStatus = "pending" | "approved" | "rejected" | "expired" | "revoked";

export type ScholarshipAward = {
  id: string;
  scholarship: string;
  scholarship_name: string;
  resident: string;
  resident_name: string;
  status: ScholarshipAwardStatus;
  valid_from: string | null;
  valid_until: string | null;
  note: string;
};

/* ---------------------------- Expenses & income --------------------------- */

export type ExpenseCategory = FeeCategory;

export type ExpenseStatus = "pending" | "approved" | "rejected" | "paid";
export type ExpenseRecurrence = "none" | "monthly" | "quarterly" | "annual";

export type Expense = {
  id: string;
  category: string;
  category_name: string;
  title: string;
  description: string;
  amount: Money;
  tax_amount: Money;
  expense_date: string;
  payment_method: PaymentMethod;
  vendor_name: string;
  vendor_contact: string;
  reference: string;
  status: ExpenseStatus;
  recurrence: ExpenseRecurrence;
};

export type IncomeSource =
  | "student_fees"
  | "room_booking"
  | "security_deposit"
  | "cafeteria"
  | "laundry"
  | "transport"
  | "internet"
  | "extra_services"
  | "commission"
  | "interest"
  | "donation"
  | "other";

export type Income = {
  id: string;
  source: IncomeSource;
  title: string;
  description: string;
  amount: Money;
  income_date: string;
  payment_method: PaymentMethod;
  reference: string;
};

/* --------------------------------- Refunds -------------------------------- */

export type RefundType =
  | "security_deposit"
  | "admission_cancellation"
  | "overpayment"
  | "scholarship_adjustment"
  | "duplicate_payment"
  | "withdrawal"
  | "custom";

export type RefundStatus = "requested" | "approved" | "rejected" | "processed";

export type Refund = {
  id: string;
  refund_type: RefundType;
  payment: string | null;
  payment_receipt: string | null;
  invoice: string | null;
  invoice_number: string | null;
  resident: string | null;
  resident_name: string | null;
  amount: Money;
  method: PaymentMethod;
  reason: string;
  status: RefundStatus;
  processed_at: string | null;
  note: string;
};

/* --------------------------------- Budgets -------------------------------- */

export type Budget = {
  id: string;
  name: string;
  category: string;
  category_name: string;
  period_year: number;
  period_month: number | null;
  amount: Money;
  spent: Money;
  note: string;
};

/* ------------------------------ Transactions ------------------------------ */

export type TransactionDirection = "in" | "out";

export type Transaction = {
  id: string;
  direction: TransactionDirection;
  category: string;
  amount: Money;
  method: PaymentMethod;
  occurred_at: string;
  entity_type: string;
  entity_id: string;
  resident: string | null;
  resident_name: string | null;
  memo: string;
};

/* --------------------------------- Reports -------------------------------- */

export type CollectionsReport = {
  start: string;
  end: string;
  rows: { date: string; total: Money; count: number }[];
};

export type ProfitLossReport = {
  start: string;
  end: string;
  income: { category: string; total: Money }[];
  expenses: { category: string; total: Money }[];
  total_income: Money;
  total_expenses: Money;
  net: Money;
};

export type ExpenseBreakdownReport = {
  start: string;
  end: string;
  rows: { category: string; total: Money; count: number }[];
};

export type DuesReport = {
  rows: {
    id: string;
    number: string;
    resident_name: string;
    status: InvoiceStatus;
    issue_date: string;
    due_date: string;
    total: Money;
    paid_amount: Money;
    balance: Money;
  }[];
};

export type ExportType = "transactions" | "invoices" | "payments" | "expenses" | "income";

/* -------------------------------- Pickers -------------------------------- */

/** Minimal resident shape used for dropdowns / searchable pickers. */
export type ResidentOption = {
  id: string;
  full_name: string;
};

/* ---------------------------- Create payloads ---------------------------- */

export type ScholarshipAwardPayload = {
  scholarship: string;
  resident: string;
  valid_from?: string;
  valid_until?: string;
  note?: string;
};

export type RefundPayload = {
  refund_type: RefundType;
  resident?: string;
  payment?: string;
  invoice?: string;
  amount: string;
  method: PaymentMethod;
  reason?: string;
  note?: string;
};

export type FeeAssignmentPayload = {
  fee_structure: string;
  resident: string;
  amount_override?: string;
  start_date?: string;
  end_date?: string;
};
