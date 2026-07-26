import { apiFetch, AUTH_TIMEOUT_MS } from "@hostel/api";

export type SignupPayload = {
  username: string;
  email: string;
  /** 6-digit code emailed by requestSignupOtp() — required to create the account. */
  otp: string;
  password: string;
  password2: string;
  hostel_name: string;
  /**
   * Permanent workspace username (subdomain: <username>.myhostel.com).
   * Optional — the backend auto-generates one from hostel_name when omitted.
   */
  workspace_username?: string;
  hostel_phone?: string;
  hostel_address?: string;
  owner_name?: string;
};

export type AuthUser = {
  id: number;
  username: string;
  email?: string;
  first_name?: string;
  last_name?: string;
  role?: string;
  is_staff?: boolean;
  is_active?: boolean;
  date_joined?: string;
  last_login?: string | null;
  hostel_code?: string | null;
  hostel_id?: string | null;
  /** When true, the account must set a new password before using the app. */
  must_change_password?: boolean;
};

export type ProfileUpdatePayload = {
  first_name?: string;
  last_name?: string;
  email?: string;
};

export type PasswordChangePayload = {
  old_password: string;
  new_password: string;
};

/** One entry in the account activity timeline (from the server audit log). */
export type ActivityEvent = {
  id: number;
  action: string;
  message?: string;
  ip_address?: string | null;
  user_agent?: string;
  created_at: string;
  meta?: Record<string, unknown>;
};

/** A live sign-in session (one active refresh token / device). */
export type SessionInfo = {
  id: number;
  created_at: string;
  expires_at: string;
  current: boolean;
  device?: string;
};

export type SignupResponse = {
  user: AuthUser;
  hostel_code?: string | null;
  /** The freshly provisioned workspace (permanent username + URL). */
  workspace?: {
    username: string;
    url: string;
    status: string;
  } | null;
  access: string;
  refresh: string;
};

export type Portal = "admin" | "staff" | "student" | "parent";

export type LoginPayload = {
  username: string;
  password: string;
  /** Required on the root domain; optional on a workspace host (the resolved
   * workspace IS the login scope). */
  hostel_id?: string;
  /** Which login surface this is — the backend rejects roles the portal
   * doesn't admit (a student can never sign in through /admin). */
  portal?: Portal;
  /** Longer refresh-token lifetime (fewer re-logins). */
  remember?: boolean;
};

export type LoginResponse = {
  detail?: string;
  user?: AuthUser;
  hostel_code?: string | null;
  workspace?: { username: string; url: string; status: string; name: string } | null;
  role?: string;
  /** Role-based dashboard the backend wants this session to land on. */
  redirect?: string;
  mfa_required?: boolean;
  /** First-login gate: redirect to /change-password before anything else. */
  must_change_password?: boolean;
};

export const authApi = {
  /** Tenant-scoped login (workspace context or legacy Hostel ID). */
  login(payload: LoginPayload) {
    return apiFetch<LoginResponse>("/auth/login/", {
      method: "POST",
      auth: false,
      body: JSON.stringify(payload),
      timeoutMs: AUTH_TIMEOUT_MS,
    });
  },

  /** Verify the current session (user + workspace + role) in one call. */
  verifySession() {
    return apiFetch<{
      authenticated: boolean;
      user: AuthUser;
      role: string;
      redirect: string;
      workspace: { username: string; url: string; name: string; status: string } | null;
    }>("/auth/session/verify/");
  },

  /** My effective permissions in the resolved workspace (backend RBAC). */
  myPermissions() {
    return apiFetch<{ role: string; permissions: string[] }>("/auth/permissions/");
  },

  /** Point-check one backend permission in this workspace. */
  checkPermission(permission: string) {
    return apiFetch<{ permission: string; allowed: boolean }>(
      "/auth/permissions/check/",
      { params: { permission } },
    );
  },

  /** Step 1: email a 6-digit verification code to the given address. */
  requestSignupOtp(payload: { email: string }) {
    return apiFetch<{ detail: string }>("/auth/signup/request-otp/", {
      method: "POST",
      auth: false,
      body: JSON.stringify(payload),
      timeoutMs: AUTH_TIMEOUT_MS,
    });
  },

  /** Step 2: create the account, supplying the verified OTP. */
  signup(payload: SignupPayload) {
    return apiFetch<SignupResponse>("/auth/signup/", {
      method: "POST",
      auth: false,
      body: JSON.stringify(payload),
      timeoutMs: AUTH_TIMEOUT_MS,
    });
  },

  me() {
    return apiFetch<AuthUser>("/auth/me/");
  },

  /** Self-service profile edit (display name + email). */
  updateMe(payload: ProfileUpdatePayload) {
    return apiFetch<AuthUser>("/auth/me/", {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  /** Change password while signed in (requires the current password). */
  changePassword(payload: PasswordChangePayload) {
    return apiFetch<{ detail: string }>("/auth/password/change/", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  /** Recent security events for the signed-in user (newest first). */
  activity(limit = 20) {
    return apiFetch<ActivityEvent[]>("/auth/activity/", { params: { limit } });
  },

  /** Live sessions (devices) for this account; the current one is flagged. */
  sessions() {
    return apiFetch<SessionInfo[]>("/auth/sessions/");
  },

  /** Sign a single other device out by session id. */
  revokeSession(id: number) {
    return apiFetch<{ detail: string }>(`/auth/sessions/${id}/`, { method: "DELETE" });
  },

  /** Revoke every session for this account (sign out of all devices). */
  logoutAll() {
    return apiFetch<{ detail: string }>("/auth/logout-all/", {
      method: "POST",
      auth: false,
    });
  },

  forgotPassword(payload: { email?: string; username?: string }) {
    return apiFetch<{ detail: string }>("/auth/password/forgot/", {
      method: "POST",
      auth: false,
      body: JSON.stringify(payload),
      timeoutMs: AUTH_TIMEOUT_MS,
    });
  },

  resetPassword(payload: { email_or_username: string; otp: string; new_password: string }) {
    return apiFetch<{ detail: string }>("/auth/password/reset/", {
      method: "POST",
      auth: false,
      body: JSON.stringify(payload),
      timeoutMs: AUTH_TIMEOUT_MS,
    });
  },

  forgotHostelID(payload: { email_or_username: string }) {
    return apiFetch<{ detail: string }>("/auth/hostel-id/forgot/", {
      method: "POST",
      auth: false,
      body: JSON.stringify(payload),
      timeoutMs: AUTH_TIMEOUT_MS,
    });
  },
};
