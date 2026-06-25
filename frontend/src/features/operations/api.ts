import { api } from "@/shared/api/apiClient";
import type { EntryExitLog, LeaveRequest, VisitorLog } from "./types";

export async function listLeaveRequests(params?: { status?: string; student?: string }) {
  const res = await api.get<LeaveRequest[]>("/operations/leave-requests/", { params });
  return res.data;
}

export async function createLeaveRequest(payload: Partial<LeaveRequest>) {
  const res = await api.post<LeaveRequest>("/operations/leave-requests/", payload);
  return res.data;
}

export async function approveLeave(id: string, decision_note = "") {
  const res = await api.post<LeaveRequest>(`/operations/leave-requests/${id}/approve/`, { decision_note });
  return res.data;
}

export async function rejectLeave(id: string, decision_note = "") {
  const res = await api.post<LeaveRequest>(`/operations/leave-requests/${id}/reject/`, { decision_note });
  return res.data;
}

export async function listVisitors(params?: { student?: string }) {
  const res = await api.get<VisitorLog[]>("/operations/visitor-logs/", { params });
  return res.data;
}

export async function createVisitor(payload: Partial<VisitorLog>) {
  const res = await api.post<VisitorLog>("/operations/visitor-logs/", payload);
  return res.data;
}

export async function checkoutVisitor(id: string) {
  const res = await api.post<VisitorLog>(`/operations/visitor-logs/${id}/checkout/`, {});
  return res.data;
}

export async function listEntryExit(params?: { direction?: string; student?: string }) {
  const res = await api.get<EntryExitLog[]>("/operations/entry-exit/", { params });
  return res.data;
}

export async function createEntryExit(payload: Partial<EntryExitLog>) {
  const res = await api.post<EntryExitLog>("/operations/entry-exit/", payload);
  return res.data;
}
