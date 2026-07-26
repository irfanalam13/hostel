import { api } from "@hostel/api";
import { offlineWrite } from "@hostel/api";
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
  // Offline-capable: a queued replay is de-duplicated server-side by its
  // idempotency key, so a lost ack can't record the same payment twice.
  return offlineWrite<Payment>("/payments/payments/", data, {
    label: `Collect payment${data.amount ? ` Rs ${data.amount}` : ""}`,
    entity: "payment",
  });
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
