import { apiFetch } from "@hostel/api";
import type {
  IPRule,
  KillSwitchTarget,
  SecurityEvent,
  SecuritySetting,
  SecuritySummary,
  TopOffender,
} from "../types/security.types";

function s<T>(path: string, options: RequestInit = {}) {
  return apiFetch<T>(`/platform/security${path}`, options);
}

const json = (body: unknown): RequestInit => ({ body: JSON.stringify(body) });

export const securityApi = {
  summary: (windowHours?: number) =>
    s<SecuritySummary>(`/summary/${windowHours ? `?window_hours=${windowHours}` : ""}`),

  events: (params: { limit?: number; offset?: number; event_type?: string; action?: string; ip?: string } = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "") qs.set(k, String(v));
    });
    const query = qs.toString();
    return s<{ count: number; results: SecurityEvent[] }>(`/events/${query ? `?${query}` : ""}`);
  },

  offenders: (windowHours?: number) =>
    s<{ offenders: TopOffender[] }>(`/offenders/${windowHours ? `?window_hours=${windowHours}` : ""}`),

  ipRules: {
    list: () => s<IPRule[]>("/ip-rules/"),
    create: (body: Partial<IPRule>) => s<IPRule>("/ip-rules/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<IPRule>) =>
      s<IPRule>(`/ip-rules/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => s<void>(`/ip-rules/${id}/`, { method: "DELETE" }),
  },

  settings: {
    list: () => s<SecuritySetting[]>("/settings/"),
    create: (body: Partial<SecuritySetting>) =>
      s<SecuritySetting>("/settings/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<SecuritySetting>) =>
      s<SecuritySetting>(`/settings/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => s<void>(`/settings/${id}/`, { method: "DELETE" }),
  },

  resolvedConfig: () => s<{ generation: number; config: Record<string, unknown> }>("/config/"),

  reputationClear: (ip: string) => s<{ detail: string }>("/reputation/clear/", { method: "POST", ...json({ ip }) }),

  report: (period: "daily" | "weekly" | "monthly" = "daily") =>
    s<Record<string, unknown>>(`/report/?period=${period}`),

  killSwitch: (target: KillSwitchTarget, engage: boolean, reason?: string) =>
    s<{ detail: string; target: string; engaged: boolean }>("/kill-switch/", {
      method: "POST",
      ...json({ target, engage, reason }),
    }),
};
