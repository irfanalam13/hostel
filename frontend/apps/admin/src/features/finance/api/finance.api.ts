import { apiDownload, apiFetch } from "@hostel/api";

import type {
  Budget,
  CollectionsReport,
  CreateInvoicePayload,
  CreatePaymentPayload,
  Discount,
  DuesReport,
  Expense,
  ExpenseBreakdownReport,
  ExpenseCategory,
  ExportType,
  FeeAssignment,
  FeeAssignmentPayload,
  FeeCategory,
  FeeStructure,
  FinanceDashboard,
  Income,
  Invoice,
  Payment,
  ProfitLossReport,
  Refund,
  RefundPayload,
  ResidentOption,
  Scholarship,
  ScholarshipAward,
  ScholarshipAwardPayload,
  Transaction,
} from "../types/finance.types";

function f<T>(path: string, options: RequestInit = {}) {
  return apiFetch<T>(`/finance${path}`, options);
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

export const financeApi = {
  dashboard: {
    summary: () => f<FinanceDashboard>("/dashboard/summary/"),
  },

  invoices: {
    list: (params: { search?: string; resident?: string; status?: string; ordering?: string } = {}) =>
      f<Invoice[]>(`/invoices/${qs(params)}`),
    retrieve: (id: string) => f<Invoice>(`/invoices/${id}/`),
    create: (body: CreateInvoicePayload) =>
      f<Invoice>("/invoices/", { method: "POST", ...json(body) }),
    cancel: (id: string) => f<Invoice>(`/invoices/${id}/cancel/`, { method: "POST", ...json({}) }),
    issue: (id: string) => f<Invoice>(`/invoices/${id}/issue/`, { method: "POST", ...json({}) }),
    remove: (id: string) => f<void>(`/invoices/${id}/`, { method: "DELETE" }),
  },

  payments: {
    list: (
      params: {
        search?: string;
        invoice?: string;
        resident?: string;
        status?: string;
        method?: string;
      } = {},
    ) => f<Payment[]>(`/payments/${qs(params)}`),
    create: (body: CreatePaymentPayload) =>
      f<Payment>("/payments/", { method: "POST", ...json(body) }),
    verify: (id: string) => f<Payment>(`/payments/${id}/verify/`, { method: "POST", ...json({}) }),
    cancel: (id: string) => f<Payment>(`/payments/${id}/cancel/`, { method: "POST", ...json({}) }),
    fail: (id: string) => f<Payment>(`/payments/${id}/fail/`, { method: "POST", ...json({}) }),
    remove: (id: string) => f<void>(`/payments/${id}/`, { method: "DELETE" }),
  },

  feeCategories: {
    list: (params: { search?: string } = {}) => f<FeeCategory[]>(`/fee-categories/${qs(params)}`),
    create: (body: Partial<FeeCategory>) =>
      f<FeeCategory>("/fee-categories/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<FeeCategory>) =>
      f<FeeCategory>(`/fee-categories/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => f<void>(`/fee-categories/${id}/`, { method: "DELETE" }),
  },

  feeStructures: {
    list: (
      params: { search?: string; category?: string; recurrence?: string; is_active?: string } = {},
    ) => f<FeeStructure[]>(`/fee-structures/${qs(params)}`),
    create: (body: Partial<FeeStructure>) =>
      f<FeeStructure>("/fee-structures/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<FeeStructure>) =>
      f<FeeStructure>(`/fee-structures/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => f<void>(`/fee-structures/${id}/`, { method: "DELETE" }),
  },

  feeAssignments: {
    list: (
      params: { search?: string; fee_structure?: string; resident?: string; status?: string } = {},
    ) => f<FeeAssignment[]>(`/fee-assignments/${qs(params)}`),
    create: (body: FeeAssignmentPayload) =>
      f<FeeAssignment>("/fee-assignments/", { method: "POST", ...json(body) }),
    bulkAssign: (body: {
      fee_structure: string;
      resident_ids: string[];
      amount_override?: string;
      start_date?: string;
    }) =>
      f<{ created: number }>("/fee-assignments/bulk-assign/", { method: "POST", ...json(body) }),
    waive: (id: string, reason: string) =>
      f<FeeAssignment>(`/fee-assignments/${id}/waive/`, { method: "POST", ...json({ reason }) }),
    remove: (id: string) => f<void>(`/fee-assignments/${id}/`, { method: "DELETE" }),
  },

  discounts: {
    list: (params: { search?: string } = {}) => f<Discount[]>(`/discounts/${qs(params)}`),
    create: (body: Partial<Discount>) =>
      f<Discount>("/discounts/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<Discount>) =>
      f<Discount>(`/discounts/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => f<void>(`/discounts/${id}/`, { method: "DELETE" }),
  },

  scholarships: {
    list: (params: { search?: string } = {}) => f<Scholarship[]>(`/scholarships/${qs(params)}`),
    create: (body: Partial<Scholarship>) =>
      f<Scholarship>("/scholarships/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<Scholarship>) =>
      f<Scholarship>(`/scholarships/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => f<void>(`/scholarships/${id}/`, { method: "DELETE" }),
  },

  scholarshipAwards: {
    list: (params: { scholarship?: string; resident?: string; status?: string } = {}) =>
      f<ScholarshipAward[]>(`/scholarship-awards/${qs(params)}`),
    create: (body: ScholarshipAwardPayload) =>
      f<ScholarshipAward>("/scholarship-awards/", { method: "POST", ...json(body) }),
    approve: (id: string) =>
      f<ScholarshipAward>(`/scholarship-awards/${id}/approve/`, { method: "POST", ...json({}) }),
    reject: (id: string) =>
      f<ScholarshipAward>(`/scholarship-awards/${id}/reject/`, { method: "POST", ...json({}) }),
    revoke: (id: string) =>
      f<ScholarshipAward>(`/scholarship-awards/${id}/revoke/`, { method: "POST", ...json({}) }),
    remove: (id: string) => f<void>(`/scholarship-awards/${id}/`, { method: "DELETE" }),
  },

  expenseCategories: {
    list: (params: { search?: string } = {}) =>
      f<ExpenseCategory[]>(`/expense-categories/${qs(params)}`),
    create: (body: Partial<ExpenseCategory>) =>
      f<ExpenseCategory>("/expense-categories/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<ExpenseCategory>) =>
      f<ExpenseCategory>(`/expense-categories/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => f<void>(`/expense-categories/${id}/`, { method: "DELETE" }),
  },

  expenses: {
    list: (
      params: { search?: string; category?: string; status?: string; payment_method?: string } = {},
    ) => f<Expense[]>(`/expenses/${qs(params)}`),
    create: (body: Partial<Expense>) => f<Expense>("/expenses/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<Expense>) =>
      f<Expense>(`/expenses/${id}/`, { method: "PATCH", ...json(body) }),
    approve: (id: string) => f<Expense>(`/expenses/${id}/approve/`, { method: "POST", ...json({}) }),
    reject: (id: string) => f<Expense>(`/expenses/${id}/reject/`, { method: "POST", ...json({}) }),
    markPaid: (id: string) =>
      f<Expense>(`/expenses/${id}/mark-paid/`, { method: "POST", ...json({}) }),
    remove: (id: string) => f<void>(`/expenses/${id}/`, { method: "DELETE" }),
  },

  income: {
    list: (params: { search?: string; source?: string; payment_method?: string } = {}) =>
      f<Income[]>(`/income/${qs(params)}`),
    create: (body: Partial<Income>) => f<Income>("/income/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<Income>) =>
      f<Income>(`/income/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => f<void>(`/income/${id}/`, { method: "DELETE" }),
  },

  refunds: {
    list: (
      params: { search?: string; refund_type?: string; status?: string; resident?: string } = {},
    ) => f<Refund[]>(`/refunds/${qs(params)}`),
    create: (body: RefundPayload) => f<Refund>("/refunds/", { method: "POST", ...json(body) }),
    approve: (id: string) => f<Refund>(`/refunds/${id}/approve/`, { method: "POST", ...json({}) }),
    reject: (id: string) => f<Refund>(`/refunds/${id}/reject/`, { method: "POST", ...json({}) }),
    process: (id: string) => f<Refund>(`/refunds/${id}/process/`, { method: "POST", ...json({}) }),
    remove: (id: string) => f<void>(`/refunds/${id}/`, { method: "DELETE" }),
  },

  budgets: {
    list: (
      params: { search?: string; category?: string; period_year?: string; period_month?: string } = {},
    ) => f<Budget[]>(`/budgets/${qs(params)}`),
    create: (body: Partial<Budget>) => f<Budget>("/budgets/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<Budget>) =>
      f<Budget>(`/budgets/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => f<void>(`/budgets/${id}/`, { method: "DELETE" }),
  },

  transactions: {
    list: (params: { direction?: string; method?: string; resident?: string; search?: string } = {}) =>
      f<Transaction[]>(`/transactions/${qs(params)}`),
  },

  reports: {
    collections: (params: { start?: string; end?: string } = {}) =>
      f<CollectionsReport>(`/reports/collections/${qs(params)}`),
    profitLoss: (params: { start?: string; end?: string } = {}) =>
      f<ProfitLossReport>(`/reports/profit-loss/${qs(params)}`),
    expenseBreakdown: (params: { start?: string; end?: string } = {}) =>
      f<ExpenseBreakdownReport>(`/reports/expense-breakdown/${qs(params)}`),
    dues: () => f<DuesReport>("/reports/dues/"),
    exportCsv: (type: ExportType) =>
      apiDownload(`/finance/reports/export/${qs({ type })}`, `finance-${type}.csv`),
  },

  // Resident picker helper — reused across invoice/payment/refund/award forms.
  residents: {
    list: (search?: string) => apiFetch<ResidentOption[]>(`/residents/${qs({ search })}`),
  },
};
