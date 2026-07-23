import { apiFetch } from "@hostel/api";

import type {
  CreateStaffPayload,
  Department,
  Designation,
  PermissionCatalog,
  Role,
  StaffCreateResult,
  StaffDocument,
  StaffProfile,
} from "../types/staff.types";

function s<T>(path: string, options: RequestInit = {}) {
  return apiFetch<T>(`/staff${path}`, options);
}

const json = (body: unknown): RequestInit => ({ body: JSON.stringify(body) });

function qs(params: Record<string, string | undefined>): string {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== "");
  if (entries.length === 0) return "";
  return "?" + entries.map(([k, v]) => `${k}=${encodeURIComponent(v as string)}`).join("&");
}

export const staffApi = {
  staff: {
    list: (params: { search?: string; status?: string; department?: string } = {}) =>
      s<StaffProfile[]>(`/${qs(params)}`),
    retrieve: (id: string) => s<StaffProfile>(`/${id}/`),
    create: (body: CreateStaffPayload) =>
      s<StaffCreateResult>("/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<CreateStaffPayload>) =>
      s<StaffProfile>(`/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => s<void>(`/${id}/`, { method: "DELETE" }),

    suspend: (id: string) => s<StaffProfile>(`/${id}/suspend/`, { method: "POST", ...json({}) }),
    activate: (id: string) => s<StaffProfile>(`/${id}/activate/`, { method: "POST", ...json({}) }),
    disable: (id: string) => s<StaffProfile>(`/${id}/disable/`, { method: "POST", ...json({}) }),
    lock: (id: string) => s<StaffProfile>(`/${id}/lock/`, { method: "POST", ...json({}) }),
    unlock: (id: string) => s<StaffProfile>(`/${id}/unlock/`, { method: "POST", ...json({}) }),
    restore: (id: string) => s<StaffProfile>(`/${id}/restore/`, { method: "POST", ...json({}) }),
    resetPassword: (id: string) =>
      s<{ detail: string; temporary_password: string }>(`/${id}/reset-password/`, {
        method: "POST",
        ...json({}),
      }),
    forcePasswordReset: (id: string) =>
      s<StaffProfile>(`/${id}/force-password-reset/`, { method: "POST", ...json({}) }),
  },

  roles: {
    list: () => s<Role[]>("/roles/"),
    retrieve: (id: string) => s<Role>(`/roles/${id}/`),
    create: (body: Partial<Role>) => s<Role>("/roles/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<Role>) =>
      s<Role>(`/roles/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => s<void>(`/roles/${id}/`, { method: "DELETE" }),
    catalog: () => s<PermissionCatalog>("/roles/catalog/"),
  },

  departments: {
    list: () => s<Department[]>("/departments/"),
    create: (body: Partial<Department>) =>
      s<Department>("/departments/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<Department>) =>
      s<Department>(`/departments/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => s<void>(`/departments/${id}/`, { method: "DELETE" }),
  },

  designations: {
    list: () => s<Designation[]>("/designations/"),
    create: (body: Partial<Designation>) =>
      s<Designation>("/designations/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<Designation>) =>
      s<Designation>(`/designations/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => s<void>(`/designations/${id}/`, { method: "DELETE" }),
  },

  documents: {
    listFor: (staffId: string) => s<StaffDocument[]>(`/documents/?staff=${staffId}`),
    remove: (id: string) => s<void>(`/documents/${id}/`, { method: "DELETE" }),
  },
};
