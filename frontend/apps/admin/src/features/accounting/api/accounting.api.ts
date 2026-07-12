import { apiDownload, apiFetch } from "@hostel/api";

import type {
  Account,
  AccountLedger,
  AccountPayload,
  AccountingDashboard,
  BalanceSheetReport,
  BankAccount,
  BankAccountPayload,
  BankStatementLine,
  BankStatementLinePayload,
  Branch,
  Budget,
  BudgetPayload,
  BudgetVarianceReport,
  CashFlowReport,
  CostCenter,
  Currency,
  ExchangeRate,
  FiscalYear,
  FixedAsset,
  FixedAssetPayload,
  AssetDepreciation,
  Journal,
  JournalPayload,
  JournalRegisterReport,
  LedgerEntry,
  Period,
  ProfitLossReport,
  ReportExportType,
  StatementOfEquityReport,
  TaxCode,
  TrendsReport,
  TrialBalanceReport,
} from "../types/accounting.types";

function f<T>(path: string, options: RequestInit = {}) {
  return apiFetch<T>(`/accounting${path}`, options);
}

const json = (body: unknown): RequestInit => ({ body: JSON.stringify(body) });

type QueryValue = string | number | boolean | undefined | null;

function qs(params: Record<string, QueryValue>): string {
  const entries = Object.entries(params).filter(
    ([, v]) => v !== undefined && v !== null && v !== "",
  );
  if (entries.length === 0) return "";
  return "?" + entries.map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`).join("&");
}

export const accountingApi = {
  dashboard: {
    summary: () => f<AccountingDashboard>("/dashboard/summary/"),
  },

  accounts: {
    list: (
      params: {
        search?: string;
        ordering?: string;
        type?: string;
        is_group?: string;
        is_active?: string;
        parent?: string;
        branch?: string;
      } = {},
    ) => f<Account[]>(`/accounts/${qs(params)}`),
    retrieve: (id: string) => f<Account>(`/accounts/${id}/`),
    create: (body: AccountPayload) => f<Account>("/accounts/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<AccountPayload>) =>
      f<Account>(`/accounts/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => f<void>(`/accounts/${id}/`, { method: "DELETE" }),
    seedDefaults: () =>
      f<{ created: number }>("/accounts/seed-defaults/", { method: "POST", ...json({}) }),
    ledger: (id: string, params: { start?: string; end?: string } = {}) =>
      f<AccountLedger>(`/accounts/${id}/ledger/${qs(params)}`),
  },

  journals: {
    list: (
      params: {
        search?: string;
        ordering?: string;
        status?: string;
        journal_type?: string;
        period?: string;
        branch?: string;
      } = {},
    ) => f<Journal[]>(`/journals/${qs(params)}`),
    retrieve: (id: string) => f<Journal>(`/journals/${id}/`),
    create: (body: JournalPayload) => f<Journal>("/journals/", { method: "POST", ...json(body) }),
    update: (id: string, body: JournalPayload) =>
      f<Journal>(`/journals/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => f<void>(`/journals/${id}/`, { method: "DELETE" }),
    submit: (id: string) => f<Journal>(`/journals/${id}/submit/`, { method: "POST", ...json({}) }),
    approve: (id: string) =>
      f<Journal>(`/journals/${id}/approve/`, { method: "POST", ...json({}) }),
    post: (id: string) => f<Journal>(`/journals/${id}/post/`, { method: "POST", ...json({}) }),
    reverse: (id: string, date?: string) =>
      f<Journal>(`/journals/${id}/reverse/`, { method: "POST", ...json(date ? { date } : {}) }),
  },

  ledger: {
    list: (
      params: {
        account?: string;
        journal?: string;
        branch?: string;
        cost_center?: string;
        ordering?: string;
      } = {},
    ) => f<LedgerEntry[]>(`/ledger/${qs(params)}`),
  },

  fiscalYears: {
    list: () => f<FiscalYear[]>("/fiscal-years/"),
    create: (body: Partial<FiscalYear>) =>
      f<FiscalYear>("/fiscal-years/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<FiscalYear>) =>
      f<FiscalYear>(`/fiscal-years/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => f<void>(`/fiscal-years/${id}/`, { method: "DELETE" }),
    generatePeriods: (id: string) =>
      f<FiscalYear>(`/fiscal-years/${id}/generate-periods/`, { method: "POST", ...json({}) }),
    postOpeningBalances: (id: string) =>
      f<FiscalYear>(`/fiscal-years/${id}/post-opening-balances/`, { method: "POST", ...json({}) }),
    close: (id: string) =>
      f<FiscalYear>(`/fiscal-years/${id}/close/`, { method: "POST", ...json({}) }),
  },

  periods: {
    list: (params: { fiscal_year?: string; is_closed?: string } = {}) =>
      f<Period[]>(`/periods/${qs(params)}`),
    close: (id: string) => f<Period>(`/periods/${id}/close/`, { method: "POST", ...json({}) }),
    reopen: (id: string) => f<Period>(`/periods/${id}/reopen/`, { method: "POST", ...json({}) }),
  },

  taxCodes: {
    list: () => f<TaxCode[]>("/tax-codes/"),
    create: (body: Partial<TaxCode>) => f<TaxCode>("/tax-codes/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<TaxCode>) =>
      f<TaxCode>(`/tax-codes/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => f<void>(`/tax-codes/${id}/`, { method: "DELETE" }),
  },

  costCenters: {
    list: () => f<CostCenter[]>("/cost-centers/"),
    create: (body: Partial<CostCenter>) =>
      f<CostCenter>("/cost-centers/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<CostCenter>) =>
      f<CostCenter>(`/cost-centers/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => f<void>(`/cost-centers/${id}/`, { method: "DELETE" }),
  },

  branches: {
    list: () => f<Branch[]>("/branches/"),
    create: (body: Partial<Branch>) => f<Branch>("/branches/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<Branch>) =>
      f<Branch>(`/branches/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => f<void>(`/branches/${id}/`, { method: "DELETE" }),
  },

  currencies: {
    list: () => f<Currency[]>("/currencies/"),
    create: (body: Partial<Currency>) =>
      f<Currency>("/currencies/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<Currency>) =>
      f<Currency>(`/currencies/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => f<void>(`/currencies/${id}/`, { method: "DELETE" }),
  },

  exchangeRates: {
    list: (params: { currency?: string } = {}) => f<ExchangeRate[]>(`/exchange-rates/${qs(params)}`),
    create: (body: Partial<ExchangeRate>) =>
      f<ExchangeRate>("/exchange-rates/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<ExchangeRate>) =>
      f<ExchangeRate>(`/exchange-rates/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => f<void>(`/exchange-rates/${id}/`, { method: "DELETE" }),
  },

  budgets: {
    list: (
      params: {
        fiscal_year?: string;
        branch?: string;
        cost_center?: string;
        is_approved?: string;
      } = {},
    ) => f<Budget[]>(`/budgets/${qs(params)}`),
    create: (body: BudgetPayload) => f<Budget>("/budgets/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<BudgetPayload>) =>
      f<Budget>(`/budgets/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => f<void>(`/budgets/${id}/`, { method: "DELETE" }),
    approve: (id: string) => f<Budget>(`/budgets/${id}/approve/`, { method: "POST", ...json({}) }),
    variance: (id: string) => f<BudgetVarianceReport>(`/budgets/${id}/variance/`),
  },

  fixedAssets: {
    list: (params: { status?: string; category?: string; branch?: string } = {}) =>
      f<FixedAsset[]>(`/fixed-assets/${qs(params)}`),
    create: (body: FixedAssetPayload) =>
      f<FixedAsset>("/fixed-assets/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<FixedAssetPayload>) =>
      f<FixedAsset>(`/fixed-assets/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => f<void>(`/fixed-assets/${id}/`, { method: "DELETE" }),
    depreciate: (id: string, date?: string) =>
      f<FixedAsset>(`/fixed-assets/${id}/depreciate/`, {
        method: "POST",
        ...json(date ? { date } : {}),
      }),
    dispose: (id: string, date?: string) =>
      f<FixedAsset>(`/fixed-assets/${id}/dispose/`, {
        method: "POST",
        ...json(date ? { date } : {}),
      }),
    depreciations: (id: string) => f<AssetDepreciation[]>(`/fixed-assets/${id}/depreciations/`),
  },

  bankAccounts: {
    list: () => f<BankAccount[]>("/bank-accounts/"),
    create: (body: BankAccountPayload) =>
      f<BankAccount>("/bank-accounts/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<BankAccountPayload>) =>
      f<BankAccount>(`/bank-accounts/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => f<void>(`/bank-accounts/${id}/`, { method: "DELETE" }),
    autoMatch: (id: string, toleranceDays?: number) =>
      f<{ matched: number }>(`/bank-accounts/${id}/auto-match/`, {
        method: "POST",
        ...json(toleranceDays != null ? { tolerance_days: toleranceDays } : {}),
      }),
  },

  bankStatementLines: {
    list: (params: { bank_account?: string; is_reconciled?: string } = {}) =>
      f<BankStatementLine[]>(`/bank-statement-lines/${qs(params)}`),
    create: (body: BankStatementLinePayload) =>
      f<BankStatementLine>("/bank-statement-lines/", { method: "POST", ...json(body) }),
    remove: (id: string) => f<void>(`/bank-statement-lines/${id}/`, { method: "DELETE" }),
    importCsv: (bankAccount: string, content: string) =>
      f<{ imported: number }>(`/bank-statement-lines/import-csv/`, {
        method: "POST",
        ...json({ bank_account: bankAccount, content }),
      }),
    reconcile: (id: string, matchedLine?: string) =>
      f<BankStatementLine>(`/bank-statement-lines/${id}/reconcile/`, {
        method: "POST",
        ...json(matchedLine ? { matched_line: matchedLine } : {}),
      }),
    unreconcile: (id: string) =>
      f<BankStatementLine>(`/bank-statement-lines/${id}/unreconcile/`, {
        method: "POST",
        ...json({}),
      }),
  },

  reports: {
    trialBalance: (params: { end?: string } = {}) =>
      f<TrialBalanceReport>(`/reports/trial-balance/${qs(params)}`),
    profitLoss: (params: { start?: string; end?: string } = {}) =>
      f<ProfitLossReport>(`/reports/profit-loss/${qs(params)}`),
    balanceSheet: (params: { end?: string } = {}) =>
      f<BalanceSheetReport>(`/reports/balance-sheet/${qs(params)}`),
    cashFlow: (params: { start?: string; end?: string } = {}) =>
      f<CashFlowReport>(`/reports/cash-flow/${qs(params)}`),
    statementOfEquity: (params: { start?: string; end?: string } = {}) =>
      f<StatementOfEquityReport>(`/reports/statement-of-equity/${qs(params)}`),
    trends: (params: { end?: string; months?: number } = {}) =>
      f<TrendsReport>(`/reports/trends/${qs(params)}`),
    journalRegister: (params: { start?: string; end?: string } = {}) =>
      f<JournalRegisterReport>(`/reports/journal-register/${qs(params)}`),
    exportCsv: (type: ReportExportType) =>
      apiDownload(`/accounting/reports/export/${qs({ type })}`, `accounting-${type}.csv`),
  },
};
