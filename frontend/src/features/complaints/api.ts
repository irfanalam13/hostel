import { api } from "@/shared/api/apiClient";
import type { Complaint, ComplaintStatus } from "./types";

export async function listComplaints(params?: { status?: string; priority?: string; search?: string }) {
  const res = await api.get<Complaint[]>("/complaints/tickets/", { params });
  return res.data;
}

export async function createComplaint(payload: Partial<Complaint>) {
  const res = await api.post<Complaint>("/complaints/tickets/", payload);
  return res.data;
}

export async function setComplaintStatus(id: string, status: ComplaintStatus) {
  const res = await api.post<Complaint>(`/complaints/tickets/${id}/set-status/`, { status });
  return res.data;
}

export async function addComplaintComment(id: string, body: string, internal = false) {
  const res = await api.post(`/complaints/tickets/${id}/add-comment/`, { body, internal });
  return res.data;
}
