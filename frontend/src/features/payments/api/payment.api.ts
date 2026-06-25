import { api } from "@/shared/api/apiClient";
import type { Payment, PaymentCreateInput, StudentDuesSummary } from "../types/payment.types";
import { getStudentLedgers } from "@/features/fees/api/fee-ledger.api";

export type PaymentListParams = {
  student?: string;
  method?: string;
  date?: string;
  search?: string;
  ordering?: string;
};

export async function getPayments(params: PaymentListParams = {}) {
  const res = await api.get<Payment[]>("/payments/payments/", { params });
  return res.data;
}

export function getPaymentsByStudent(studentId: string) {
  return getPayments({ student: studentId, ordering: "-date" });
}

export async function createPayment(data: PaymentCreateInput) {
  const res = await api.post<Payment>("/payments/payments/", data);
  return res.data;
}

export async function getStudentDuesSummary(studentId: string): Promise<StudentDuesSummary> {
  const ledgers = await getStudentLedgers(studentId);
  const totalDue = ledgers.reduce((sum, ledger) => sum + Number(ledger.net_due || "0"), 0);
  const unpaid = ledgers.filter((ledger) => ledger.status === "DUE" || ledger.status === "PARTIAL");
  const balance = unpaid.reduce((sum, ledger) => sum + Number(ledger.net_due || "0"), 0);

  return {
    student: studentId,
    total_due: totalDue.toFixed(2),
    total_paid: Math.max(0, totalDue - balance).toFixed(2),
    balance: balance.toFixed(2),
  };
}
