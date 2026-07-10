/** Workspace (tenant) types — mirrors /api/tenants/workspaces/. */

export type WorkspaceStatus =
  | "pending"
  | "trial"
  | "active"
  | "suspended"
  | "expired"
  | "archived";

export type Workspace = {
  id: string;
  name: string;
  code: string;
  /** Permanent workspace username — also the subdomain label. Never changes. */
  slug: string;
  subdomain: string;
  workspace_url: string;
  status: WorkspaceStatus;
  is_active: boolean;
  trial_ends_at?: string | null; // yyyy-mm-dd

  phone?: string;
  address?: string;
  owner_name?: string;

  timezone?: string;
  currency?: string;
  language?: string;
  logo?: string | null;

  plan_name?: string | null;
  subscription_active_until?: string | null;
  settings?: Record<string, unknown>;

  created_at: string;
  updated_at?: string;
};

export type WorkspaceRegisterInput = {
  hostel_name: string;
  /** Optional — auto-generated from hostel_name when omitted. */
  workspace_username?: string;
  phone?: string;
  address?: string;
  timezone?: string;
  currency?: string;
  language?: string;
};

/** Editable display fields (the slug is permanent and rejected server-side). */
export type WorkspaceUpdateInput = Partial<
  Pick<
    Workspace,
    "name" | "phone" | "address" | "owner_name" | "timezone" | "currency" | "language" | "settings"
  >
>;

/** Safe, unauthenticated branding for workspace login pages. */
export type WorkspacePublicInfo = {
  name: string;
  workspace_username: string;
  workspace_url: string;
  status: WorkspaceStatus;
  logo: string;
  language?: string;
  currency?: string;
  timezone?: string;
};

export type WorkspaceAvailability = {
  username: string;
  available: boolean;
  /** null when available; otherwise taken | reserved | invalid | too_short | too_long | required */
  reason: string | null;
  detail: string;
  suggestions: string[];
};
