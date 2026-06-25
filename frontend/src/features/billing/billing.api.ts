import { api } from "@/shared/api/apiClient";
import type { BillingPayment, BillingSummary, MonthlyDue } from "./billing.types";

export async function listDues(params?: { resident?: string; year?: number; month?: number }) {
  const res = await api.get<MonthlyDue[]>("/billing/dues/", { params });
  return res.data;
}

export async function createDue(payload: Partial<MonthlyDue>) {
  const res = await api.post<MonthlyDue>("/billing/dues/", payload);
  return res.data;
}

export async function listBillingPayments(params?: { resident?: string; due?: string; method?: string }) {
  const res = await api.get<BillingPayment[]>("/billing/payments/", { params });
  return res.data;
}

export async function createBillingPayment(payload: Partial<BillingPayment>) {
  const res = await api.post<BillingPayment>("/billing/payments/", payload);
  return res.data;
}

export async function getBillingSummary() {
  const res = await api.get<BillingSummary>("/billing/dashboard/summary/");
  return res.data;
}

export const listInvoices = listDues;
export const createInvoice = createDue;
export const listLedger = listBillingPayments;
