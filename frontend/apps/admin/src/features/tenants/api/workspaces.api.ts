import { apiFetch } from "@hostel/api";
import type {
  Workspace,
  WorkspaceAvailability,
  WorkspacePublicInfo,
  WorkspaceRegisterInput,
  WorkspaceUpdateInput,
} from "../types/workspaces.types";

/** Client for /api/tenants/workspaces/ (workspace = one hostel = one tenant). */
export const workspacesApi = {
  /**
   * Real-time workspace-username availability (public endpoint, rate-limited
   * server-side at 30/min per IP — callers should debounce).
   */
  checkAvailability(username: string, options?: { signal?: AbortSignal }) {
    return apiFetch<WorkspaceAvailability>("/tenants/workspaces/availability/", {
      auth: false,
      params: { username },
      signal: options?.signal,
    });
  },

  /**
   * Public branding for the resolved workspace's login pages (name, logo,
   * workspace username). Requires workspace context — rejects with a
   * workspace_* error code (see isWorkspaceError) when the workspace is
   * unknown, suspended or expired, which login pages render as error screens.
   */
  publicInfo() {
    return apiFetch<WorkspacePublicInfo>("/tenants/workspaces/public/", { auth: false });
  },

  /** Register an additional workspace for the signed-in user. */
  register(payload: WorkspaceRegisterInput) {
    return apiFetch<Workspace>("/tenants/workspaces/", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  /** Workspaces the signed-in user is a member of. */
  list() {
    return apiFetch<Workspace[] | { results: Workspace[] }>("/tenants/workspaces/");
  },

  /** The workspace resolved for this request (subdomain / headers / token). */
  current() {
    return apiFetch<Workspace>("/tenants/workspaces/current/");
  },

  retrieve(id: string) {
    return apiFetch<Workspace>(`/tenants/workspaces/${id}/`);
  },

  /** Update display/locale fields — the workspace username is permanent. */
  update(id: string, payload: WorkspaceUpdateInput) {
    return apiFetch<Workspace>(`/tenants/workspaces/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  suspend(id: string, reason?: string) {
    return apiFetch<Workspace>(`/tenants/workspaces/${id}/suspend/`, {
      method: "POST",
      body: JSON.stringify(reason ? { reason } : {}),
    });
  },

  archive(id: string) {
    return apiFetch<Workspace>(`/tenants/workspaces/${id}/archive/`, { method: "POST" });
  },

  restore(id: string) {
    return apiFetch<Workspace>(`/tenants/workspaces/${id}/restore/`, { method: "POST" });
  },

  /** Soft delete — data is preserved; the workspace disappears from routing. */
  remove(id: string) {
    return apiFetch<void>(`/tenants/workspaces/${id}/`, { method: "DELETE" });
  },
};
