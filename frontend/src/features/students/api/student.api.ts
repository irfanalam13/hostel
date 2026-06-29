// src/features/students/api/student.api.ts
import { apiFetch } from "@/shared/api/apiClient";
import { offlineWrite } from "@/shared/api/offlineWrite";
import type { Student } from "../types/student.types";

export type StudentListParams = {
  search?: string;
  status?: "ACTIVE" | "INACTIVE" | "LEFT" | "";
  ordering?: string;
};

export function getStudents(params: StudentListParams = {}) {
  const q = new URLSearchParams();

  if (params.search) q.set("search", params.search);
  if (params.status) q.set("status", params.status);
  if (params.ordering) q.set("ordering", params.ordering);

  const qs = q.toString() ? `?${q.toString()}` : "";
  return apiFetch<Student[]>(`/students/students/${qs}`);
}

export function getStudent(id: number | string) {
  return apiFetch<Student>(`/students/students/${id}/`);
}

export function createStudent(data: Partial<Student>) {
  // Offline-capable: queued + replayed with an idempotency key when offline.
  return offlineWrite<Student>(`/students/students/`, data, {
    label: `Register student${data.full_name ? `: ${data.full_name}` : ""}`,
    entity: "student",
  });
}

export function updateStudentPartial(id: string, data: Partial<Student>) {
  return apiFetch<Student>(`/students/students/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteStudent(id: string) {
  await apiFetch<void>(`/students/students/${id}/`, { method: "DELETE" });
}

export async function transferStudentBed(id: string, payload: { bed: string; start_date?: string }) {
  return apiFetch<{ detail: string; assignment: string }>(`/students/students/${id}/transfer-bed/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function checkoutStudent(id: string, checkout_date?: string) {
  return apiFetch<{ detail: string }>(`/students/students/${id}/checkout/`, {
    method: "POST",
    body: JSON.stringify({ checkout_date }),
  });
}

export async function getStudentTimeline(id: string) {
  return apiFetch<
    Array<{ type: string; date: string; label: string; status: string; amount?: string }>
  >(`/students/students/${id}/timeline/`);
}
