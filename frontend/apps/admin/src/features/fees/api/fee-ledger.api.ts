import { api } from "@hostel/api";
import type { FeeLedger } from "../types/fee-ledger.types";

export async function getStudentLedgers(studentId: string) {
  const res = await api.get<FeeLedger[]>("/fees/ledgers/", {
    params: {
      student: studentId,
      ordering: "-id",
    },
  });
  return res.data;
}

export async function getLedgers(params?: { month?: string; status?: string; student?: string }) {
  const res = await api.get<FeeLedger[]>("/fees/ledgers/", { params });
  return res.data;
}

export async function generateMonth(month?: string) {
  const res = await api.post<{ month: string; created: number }>("/fees/ledgers/generate_month/", {
    month,
  });
  return res.data;
}
