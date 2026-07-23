import { apiFetch } from "@hostel/api";

import type {
  Announcement,
  FeatureFlag,
  FeatureFlagOverride,
  Incident,
  LookupResult,
  MaintenanceWindow,
  OpsStatus,
} from "../types/opsgov.types";

/** Authenticated status feed for the global banner (all zones/roles). */
export function fetchOpsStatus() {
  return apiFetch<OpsStatus>("/ops/status/");
}

function p<T>(path: string, options: RequestInit = {}) {
  return apiFetch<T>(`/platform/ops${path}`, options);
}
const json = (body: unknown): RequestInit => ({ body: JSON.stringify(body) });

// DRF list endpoints are paginated; these consoles show the full set.
interface Paged<T> {
  results?: T[];
}
async function all<T>(path: string): Promise<T[]> {
  const data = await apiFetch<T[] | Paged<T>>(`/platform/ops${path}`);
  return Array.isArray(data) ? data : data.results ?? [];
}

export const opsGovApi = {
  announcements: {
    list: () => all<Announcement>("/announcements/"),
    create: (body: Partial<Announcement>) =>
      p<Announcement>("/announcements/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<Announcement>) =>
      p<Announcement>(`/announcements/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => p<void>(`/announcements/${id}/`, { method: "DELETE" }),
  },

  maintenance: {
    list: () => all<MaintenanceWindow>("/maintenance/"),
    create: (body: Partial<MaintenanceWindow>) =>
      p<MaintenanceWindow>("/maintenance/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<MaintenanceWindow>) =>
      p<MaintenanceWindow>(`/maintenance/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => p<void>(`/maintenance/${id}/`, { method: "DELETE" }),
    start: (id: string) => p<MaintenanceWindow>(`/maintenance/${id}/start/`, { method: "POST", ...json({}) }),
    complete: (id: string) =>
      p<MaintenanceWindow>(`/maintenance/${id}/complete/`, { method: "POST", ...json({}) }),
  },

  incidents: {
    list: () => all<Incident>("/incidents/"),
    create: (body: Partial<Incident>) =>
      p<Incident>("/incidents/", { method: "POST", ...json(body) }),
    remove: (id: string) => p<void>(`/incidents/${id}/`, { method: "DELETE" }),
    addUpdate: (id: string, body: { status: string; message: string }) =>
      p<Incident>(`/incidents/${id}/updates/`, { method: "POST", ...json(body) }),
  },

  flags: {
    list: () => all<FeatureFlag>("/feature-flags/"),
    create: (body: Partial<FeatureFlag>) =>
      p<FeatureFlag>("/feature-flags/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<FeatureFlag>) =>
      p<FeatureFlag>(`/feature-flags/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => p<void>(`/feature-flags/${id}/`, { method: "DELETE" }),
    kill: (id: string, kill: boolean) =>
      p<FeatureFlag>(`/feature-flags/${id}/kill/`, { method: "POST", ...json({ kill }) }),
  },

  overrides: {
    list: (flagId?: string) =>
      all<FeatureFlagOverride>(`/overrides/${flagId ? `?flag=${flagId}` : ""}`),
    create: (body: Partial<FeatureFlagOverride>) =>
      p<FeatureFlagOverride>("/overrides/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<FeatureFlagOverride>) =>
      p<FeatureFlagOverride>(`/overrides/${id}/`, { method: "PATCH", ...json(body) }),
    revoke: (id: string) =>
      p<FeatureFlagOverride>(`/overrides/${id}/revoke/`, { method: "POST", ...json({}) }),
    reactivate: (id: string) =>
      p<FeatureFlagOverride>(`/overrides/${id}/reactivate/`, { method: "POST", ...json({}) }),
    remove: (id: string) => p<void>(`/overrides/${id}/`, { method: "DELETE" }),
  },

  lookups: {
    hostels: (q: string) =>
      apiFetch<{ results: LookupResult[] }>("/platform/ops/lookup/hostels/", { params: { q } })
        .then((r) => r.results),
    users: (q: string) =>
      apiFetch<{ results: LookupResult[] }>("/platform/ops/lookup/users/", { params: { q } })
        .then((r) => r.results),
  },
};
