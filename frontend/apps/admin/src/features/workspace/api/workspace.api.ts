import { apiFetch } from "@hostel/api";

export type WorkspaceOverview = {
  workspace: {
    id: string; name: string; slug: string; workspace_url: string; code: string;
    status: string; is_active: boolean; created_at: string; updated_at?: string;
    logo?: string | null; trial_ends_at?: string | null; plan_name?: string | null;
  };
  owner: string | null;
  counts: {
    members: number; staff: number; students: number; parents: number;
    residents: number; active_users_30d: number;
  };
  last_login: string | null;
  storage_bytes: number;
  subscription: {
    plan: string | null; status: string; trial_ends_at: string | null;
    trial_days_left: number | null; active_until: string | null;
  };
  inquiries: number;
};

export type SettingsNamespace =
  | "profile" | "business" | "regional" | "notifications"
  | "security" | "preferences" | "branding" | "white_label";

export type NamespacePayload = {
  namespace: string;
  settings: Record<string, unknown>;
  defaults?: Record<string, unknown>;
};

export type TeamMember = {
  user_id: number;
  username: string;
  email: string;
  name: string;
  role: string;
  is_active: boolean;
  is_owner: boolean;
  last_login: string | null;
  joined_at: string;
};

export type ActivityEntry = {
  id: number;
  action: string;
  entity_type: string;
  message: string;
  actor: string | null;
  ip_address: string | null;
  user_agent: string;
  created_at: string;
  meta: Record<string, unknown>;
};

export const workspaceApi = {
  overview: () => apiFetch<WorkspaceOverview>("/tenants/manage/overview/"),

  getSettings: (ns: SettingsNamespace) =>
    apiFetch<NamespacePayload>(`/tenants/manage/settings/${ns}/`),
  updateSettings: (ns: SettingsNamespace, data: Record<string, unknown>) =>
    apiFetch<NamespacePayload>(`/tenants/manage/settings/${ns}/`, {
      method: "PATCH", body: JSON.stringify(data),
    }),

  rename: (workspace_username: string, password: string) =>
    apiFetch<{ detail: string; workspace: { slug: string; workspace_url: string } }>(
      "/tenants/manage/rename/",
      { method: "POST", body: JSON.stringify({ workspace_username, password }) },
    ),

  activity: (params?: { action?: string; q?: string; limit?: number }) =>
    apiFetch<ActivityEntry[]>("/tenants/manage/activity/", { params }),

  team: () => apiFetch<TeamMember[]>("/tenants/manage/team/"),
  invite: (payload: { username: string; email?: string; role: string }) =>
    apiFetch<{ detail: string; username: string; role: string; temporary_password: string }>(
      "/tenants/manage/team/",
      { method: "POST", body: JSON.stringify(payload) },
    ),
  changeRole: (userId: number, role: string) =>
    apiFetch<{ detail: string }>(`/tenants/manage/team/${userId}/`, {
      method: "PATCH", body: JSON.stringify({ role }),
    }),
  removeMember: (userId: number) =>
    apiFetch<void>(`/tenants/manage/team/${userId}/`, { method: "DELETE" }),

  danger: (action: string, password: string) =>
    apiFetch<{ detail: string }>(`/tenants/manage/danger/${action}/`, {
      method: "POST", body: JSON.stringify({ password }),
    }),
  exportSettings: () =>
    apiFetch<{ workspace_username: string; exported_at: string; settings: Record<string, unknown> }>(
      "/tenants/manage/export/",
    ),
  importSettings: (settings: Record<string, unknown>, password: string) =>
    apiFetch<{ detail: string }>("/tenants/manage/export/", {
      method: "POST", body: JSON.stringify({ settings, password }),
    }),
};
