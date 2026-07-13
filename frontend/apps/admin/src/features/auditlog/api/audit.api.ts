import { apiDownload, apiFetch } from "@hostel/api";

import type {
  AuditEvent,
  AuditFilters,
  AuditVerifyResult,
  Paginated,
} from "../types/audit.types";

function queryParams(filters: AuditFilters): Record<string, string | number> {
  const params: Record<string, string | number> = {};
  if (filters.action) params.action = filters.action;
  if (filters.result) params.result = filters.result;
  if (filters.search) params.search = filters.search;
  if (filters.created_after) params.created_after = filters.created_after;
  if (filters.created_before) params.created_before = filters.created_before;
  if (filters.page) params.page = filters.page;
  return params;
}

export const auditApi = {
  list: (filters: AuditFilters = {}) =>
    apiFetch<Paginated<AuditEvent>>("/audit/events/", { params: queryParams(filters) }),

  verify: (limit?: number) =>
    apiFetch<AuditVerifyResult>("/audit/events/verify/", {
      params: limit ? { limit } : undefined,
    }),

  exportCsv: (filters: AuditFilters = {}) => {
    const qs = new URLSearchParams(
      Object.entries(queryParams(filters)).map(([k, v]) => [k, String(v)]),
    ).toString();
    return apiDownload(`/audit/events/export/${qs ? `?${qs}` : ""}`, "audit-events.csv");
  },
};
