// src/features/students/api/student.api.ts
import { apiFetch } from "@hostel/api";
import type { Student } from "../types/student.types";

export type StudentListParams = {
  search?: string;
  status?: "ACTIVE" | "LEFT" | "";
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

// Note: students are created only via admission approval (backend blocks
// direct POST /students/students/ with 405). No createStudent() here by design.

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
