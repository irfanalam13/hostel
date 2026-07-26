import { api } from "@hostel/api";
import { offlineWrite } from "@hostel/api";
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
  // Offline-capable: gate staff can log visitors without connectivity.
  return offlineWrite<VisitorLog>("/operations/visitor-logs/", payload, {
    label: `Visitor entry${payload.visitor_name ? `: ${payload.visitor_name}` : ""}`,
    entity: "visitor",
  });
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
  // Offline-capable gate log.
  return offlineWrite<EntryExitLog>("/operations/entry-exit/", payload, {
    label: `Gate ${payload.direction || "entry/exit"} log`,
    entity: "entry_exit",
  });
}
