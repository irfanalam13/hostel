import { api } from "@hostel/api";
import type { Notice } from "./types";

export async function listNotices(params?: { search?: string; target_type?: string; is_pinned?: boolean }) {
  const res = await api.get<Notice[]>("/notices/", { params });
  return res.data;
}

export async function createNotice(payload: Partial<Notice>) {
  const res = await api.post<Notice>("/notices/", payload);
  return res.data;
}

export async function updateNotice(id: string, payload: Partial<Notice>) {
  const res = await api.patch<Notice>(`/notices/${id}/`, payload);
  return res.data;
}
