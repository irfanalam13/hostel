import { api, apiDownload } from "@/shared/api/apiClient";
import type {
  AdmissionAnalytics,
  AdmissionDecisionPayload,
  AdmissionDocType,
  AdmissionDocument,
  AdmissionRequest,
} from "./types";

export type AdmissionListParams = {
  status?: string;
  source?: string;
  gender?: string;
  food_preference?: string;
  current_level?: string;
  preferred_room_type?: string;
  district?: string;
  payment_status?: string;
  search?: string;
  ordering?: string;
};

// The DRF list endpoint is paginated; tolerate both the envelope-unwrapped
// array and a {results: []} page shape.
type Paginated<T> = { results: T[] } | T[];

function asArray<T>(data: Paginated<T>): T[] {
  return Array.isArray(data) ? data : data.results ?? [];
}

export async function listAdmissions(params?: AdmissionListParams) {
  const res = await api.get<Paginated<AdmissionRequest>>("/admissions/requests/", { params });
  return asArray(res.data);
}

export async function getAdmission(id: string) {
  const res = await api.get<AdmissionRequest>(`/admissions/requests/${id}/`);
  return res.data;
}

export async function createAdmission(payload: Partial<AdmissionRequest>) {
  const res = await api.post<AdmissionRequest>("/admissions/requests/", payload);
  return res.data;
}

export async function updateAdmission(id: string, payload: Partial<AdmissionRequest>) {
  const res = await api.patch<AdmissionRequest>(`/admissions/requests/${id}/`, payload);
  return res.data;
}

export async function deleteAdmission(id: string) {
  await api.delete(`/admissions/requests/${id}/`);
}

export async function approveAdmission(id: string, payload: AdmissionDecisionPayload) {
  const res = await api.post<AdmissionRequest>(`/admissions/requests/${id}/approve/`, payload);
  return res.data;
}

export async function rejectAdmission(id: string, decision_note = "", rejection_reason = "") {
  const res = await api.post<AdmissionRequest>(`/admissions/requests/${id}/reject/`, {
    decision_note,
    rejection_reason,
  });
  return res.data;
}

export async function assignBed(id: string, bed: string) {
  const res = await api.post<AdmissionRequest>(`/admissions/requests/${id}/assign-bed/`, { bed });
  return res.data;
}

export async function uploadDocument(id: string, doc_type: AdmissionDocType, file: File) {
  const fd = new FormData();
  fd.append("doc_type", doc_type);
  fd.append("file", file);
  const res = await api.post<AdmissionDocument>(`/admissions/requests/${id}/upload-document/`, fd);
  return res.data;
}

export async function bulkApprove(ids: string[]) {
  const res = await api.post<{ approved_count: number; errors: string[] }>(
    "/admissions/requests/bulk-approve/",
    { ids }
  );
  return res.data;
}

export async function bulkReject(ids: string[]) {
  const res = await api.post<{ rejected_count: number }>("/admissions/requests/bulk-reject/", {
    ids,
  });
  return res.data;
}

export async function getAnalytics() {
  const res = await api.get<AdmissionAnalytics>("/admissions/requests/analytics/");
  return res.data;
}

export function downloadAdmissionPdf(id: string, applicationNumber?: string) {
  return apiDownload(
    `/admissions/requests/${id}/pdf/`,
    applicationNumber ? `Admission_Form_${applicationNumber}.pdf` : undefined
  );
}

export function exportAdmissionsExcel() {
  return apiDownload("/admissions/requests/export-excel/");
}
