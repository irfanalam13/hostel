/** Money values from the backend are decimal strings (e.g. "1250.00"). */
export type Money = string;

export type AccountType = "asset" | "liability" | "equity" | "income" | "expense";
export type NormalBalance = "debit" | "credit";

export type JournalStatus = "draft" | "submitted" | "approved" | "posted" | "reversed";
export type JournalType =
  | "manual"
  | "automatic"
  | "recurring"
  | "adjustment"
  | "opening"
  | "closing"
  | "reversal"
  | "depreciation";

export type TaxType =
  | "vat"
  | "gst"
  | "sales"
  | "service"
  | "withholding"
  | "income"
  | "local"
  | "custom";

export type BudgetPeriodType = "annual" | "quarterly" | "monthly";

export type DepreciationMethod = "straight_line" | "declining_balance" | "none";
export type AssetStatus = "active" | "disposed" | "fully_depreciated";

/* ------------------------------- Dashboard ------------------------------- */

export type DashboardTotals = {
  total_assets: Money;
  total_liabilities: Money;
  total_equity: Money;
  net_income: Money;
  revenue: Money;
  expenses: Money;
  cash_bank: Money;
  accounts_receivable: Money;
  accounts_payable: Money;
  ending_cash: Money;
  working_capital: Money;
  current_ratio: string | null;
};

export type AccountingDashboard = {
  as_of: string;
  period: { start: string; end: string };
  totals: DashboardTotals;
  balance_sheet_balanced: boolean;
  pending_approvals: number;
  draft_journals: number;
  account_counts: Record<string, number>;
  recent_journals: Journal[];
};

/* -------------------------------- Accounts ------------------------------- */

export type Account = {
  id: string;
  code: string;
  name: string;
  type: AccountType;
  type_display: string;
  subtype: string;
  parent: string | null;
  parent_code: string | null;
  is_group: boolean;
  description: string;
  opening_balance: Money;
  currency: string;
  branch: string | null;
  cost_center: string | null;
  normal_balance: NormalBalance;
  is_system: boolean;
  is_active: boolean;
};

export type AccountPayload = {
  code?: string;
  name: string;
  type?: AccountType;
  subtype?: string;
  parent?: string | null;
  is_group?: boolean;
  description?: string;
  opening_balance?: string;
  currency?: string;
  branch?: string | null;
  cost_center?: string | null;
  is_active?: boolean;
};

export type LedgerRow = {
  id: string;
  date: string;
  journal_number: string;
  description: string;
  debit: Money;
  credit: Money;
  balance: Money;
};

export type AccountLedger = {
  account: {
    id: string;
    code: string;
    name: string;
    type: AccountType;
    normal_balance: NormalBalance;
  };
  opening_balance: Money;
  rows: LedgerRow[];
  closing_balance: Money;
};

/* -------------------------------- Journals ------------------------------- */

export type JournalLine = {
  id: string;
  account: string;
  account_code: string;
  account_name: string;
  debit: Money;
  credit: Money;
  description: string;
  cost_center: string | null;
  branch: string | null;
};

export type Journal = {
  id: string;
  number: string;
  date: string;
  posting_date: string | null;
  reference: string;
  description: string;
  journal_type: JournalType;
  status: JournalStatus;
  status_display: string;
  period: string | null;
  branch: string | null;
  currency: string;
  exchange_rate: Money;
  total_debit: Money;
  total_credit: Money;
  is_balanced: boolean;
  is_locked: boolean;
  notes: string;
  reverses: string | null;
  lines: JournalLine[];
  created_at: string;
};

export type JournalLinePayload = {
  account: string;
  debit?: string;
  credit?: string;
  description?: string;
  cost_center?: string | null;
  branch?: string | null;
};

export type JournalPayload = {
  date?: string;
  posting_date?: string;
  reference?: string;
  description?: string;
  journal_type?: JournalType;
  branch?: string | null;
  currency?: string;
  exchange_rate?: string;
  notes?: string;
  post?: boolean;
  lines: JournalLinePayload[];
};

/* ------------------------------ Ledger entries ---------------------------- */

export type LedgerEntry = {
  id: string;
  account: string;
  account_code: string;
  account_name: string;
  journal: string;
  journal_number: string;
  date: string;
  debit: Money;
  credit: Money;
  description: string;
};

/* ----------------------------- Fiscal years ------------------------------ */

export type Period = {
  id: string;
  fiscal_year: string;
  name: string;
  start_date: string;
  end_date: string;
  is_closed: boolean;
  closed_at: string | null;
};

export type FiscalYear = {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  is_closed: boolean;
  closed_at: string | null;
  periods: Period[];
};

/* ------------------------------- Setup data ------------------------------ */

export type TaxCode = {
  id: string;
  name: string;
  tax_type: TaxType;
  rate: Money;
  payable_account: string | null;
  receivable_account: string | null;
  is_active: boolean;
};

export type CostCenter = {
  id: string;
  name: string;
  code: string;
  description: string;
  is_active: boolean;
};

export type Branch = {
  id: string;
  name: string;
  code: string;
  is_active: boolean;
};

export type Currency = {
  id: string;
  code: string;
  name: string;
  symbol: string;
  is_base: boolean;
  is_active: boolean;
};

export type ExchangeRate = {
  id: string;
  currency: string;
  currency_code: string;
  rate_to_base: Money;
  as_of: string;
};

/* -------------------------------- Budgets -------------------------------- */

export type BudgetLine = {
  id: string;
  account: string;
  account_code: string;
  account_name: string;
  amount: Money;
  period_month: number | null;
};

export type Budget = {
  id: string;
  name: string;
  fiscal_year: string;
  period_type: BudgetPeriodType;
  branch: string | null;
  cost_center: string | null;
  is_approved: boolean;
  lines: BudgetLine[];
};

export type BudgetLinePayload = {
  account: string;
  amount: string;
  period_month?: number | null;
};

export type BudgetPayload = {
  name: string;
  fiscal_year: string;
  period_type: BudgetPeriodType;
  branch?: string | null;
  cost_center?: string | null;
  lines: BudgetLinePayload[];
};

/* ------------------------------ Fixed assets ----------------------------- */

export type FixedAsset = {
  id: string;
  name: string;
  category: string;
  code: string;
  purchase_cost: Money;
  purchase_date: string;
  useful_life_months: number;
  salvage_value: Money;
  depreciation_method: DepreciationMethod;
  declining_rate: Money;
  accumulated_depreciation: Money;
  net_book_value: Money;
  status: AssetStatus;
  disposed_date: string | null;
  asset_account: string | null;
  depreciation_expense_account: string | null;
  accumulated_depreciation_account: string | null;
  branch: string | null;
};

export type FixedAssetPayload = {
  name: string;
  category?: string;
  code?: string;
  purchase_cost: string;
  purchase_date: string;
  useful_life_months?: number;
  salvage_value?: string;
  depreciation_method?: DepreciationMethod;
  declining_rate?: string;
  asset_account?: string | null;
  depreciation_expense_account?: string | null;
  accumulated_depreciation_account?: string | null;
  branch?: string | null;
};

export type AssetDepreciation = {
  id: string;
  date: string;
  amount: Money;
  accumulated_depreciation: Money;
  net_book_value: Money;
  journal: string | null;
  journal_number: string | null;
};

/* -------------------------------- Banking -------------------------------- */

export type BankAccount = {
  id: string;
  name: string;
  account: string;
  account_name: string;
  bank_name: string;
  account_number: string;
  is_active: boolean;
};

export type BankAccountPayload = {
  name: string;
  account: string;
  bank_name?: string;
  account_number?: string;
  is_active?: boolean;
};

export type BankStatementLine = {
  id: string;
  bank_account: string;
  date: string;
  description: string;
  reference: string;
  amount: Money;
  is_reconciled: boolean;
  matched_line: string | null;
  reconciled_at: string | null;
};

export type BankStatementLinePayload = {
  bank_account: string;
  date: string;
  description?: string;
  reference?: string;
  amount: string;
};

/* --------------------------------- Reports -------------------------------- */

export type TrialBalanceRow = {
  account_id: string;
  code: string;
  name: string;
  type: AccountType;
  debit: Money;
  credit: Money;
};

export type TrialBalanceReport = {
  as_of: string;
  rows: TrialBalanceRow[];
  total_debit: Money;
  total_credit: Money;
  balanced: boolean;
};

export type ProfitLossRow = {
  code: string;
  name: string;
  subtype: string;
  amount: Money;
};

export type ProfitLossReport = {
  start: string;
  end: string;
  income: ProfitLossRow[];
  expenses: ProfitLossRow[];
  total_income: Money;
  total_expenses: Money;
  net_profit: Money;
};

export type BalanceSheetRow = {
  code: string;
  name: string;
  amount: Money;
};

export type BalanceSheetReport = {
  as_of: string;
  assets: BalanceSheetRow[];
  liabilities: BalanceSheetRow[];
  equity: BalanceSheetRow[];
  total_assets: Money;
  total_liabilities: Money;
  total_equity: Money;
  total_liabilities_equity: Money;
  balanced: boolean;
};

export type CashFlowReport = {
  start: string;
  end: string;
  beginning_cash: Money;
  inflow: Money;
  outflow: Money;
  net_change: Money;
  ending_cash: Money;
};

export type JournalRegisterRow = {
  id: string;
  number: string;
  date: string;
  description: string;
  amount: Money;
  type: string;
};

export type JournalRegisterReport = {
  start: string;
  end: string;
  rows: JournalRegisterRow[];
};

export type EquityComponent = {
  account_id: string | null;
  code: string;
  name: string;
  opening: Money;
  movement: Money;
  closing: Money;
};

export type StatementOfEquityReport = {
  start: string;
  end: string;
  components: EquityComponent[];
  opening_equity: Money;
  net_income: Money;
  movement: Money;
  closing_equity: Money;
};

export type TrendPoint = {
  month: string;
  label: string;
  revenue: Money;
  expenses: Money;
  profit: Money;
  cash_in: Money;
  cash_out: Money;
  net_cash: Money;
};

export type TrendsReport = {
  start: string;
  end: string;
  months: number;
  series: TrendPoint[];
};

export type BudgetVarianceRow = {
  account_id: string;
  code: string;
  name: string;
  type: AccountType;
  budget: Money;
  actual: Money;
  variance: Money;
  utilization: string | null;
};

export type BudgetVarianceReport = {
  budget_id: string;
  name: string;
  fiscal_year: string;
  rows: BudgetVarianceRow[];
  total_budget: Money;
  total_actual: Money;
  total_variance: Money;
};

export type ReportExportType =
  | "trial-balance"
  | "general-ledger"
  | "profit-loss"
  | "balance-sheet"
  | "journal-register";
