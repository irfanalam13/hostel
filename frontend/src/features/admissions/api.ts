import { api } from "@/shared/api/apiClient";
import type { AdmissionRequest } from "./types";

export async function listAdmissions(params?: { status?: string; search?: string }) {
  const res = await api.get<AdmissionRequest[]>("/admissions/requests/", { params });
  return res.data;
}

export async function createAdmission(payload: Partial<AdmissionRequest>) {
  const res = await api.post<AdmissionRequest>("/admissions/requests/", payload);
  return res.data;
}

export async function approveAdmission(id: string, payload: { bed?: string; join_date?: string; decision_note?: string }) {
  const res = await api.post<AdmissionRequest>(`/admissions/requests/${id}/approve/`, payload);
  return res.data;
}

export async function rejectAdmission(id: string, decision_note = "") {
  const res = await api.post<AdmissionRequest>(`/admissions/requests/${id}/reject/`, { decision_note });
  return res.data;
}
