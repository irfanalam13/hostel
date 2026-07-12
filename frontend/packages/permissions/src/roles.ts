/**
 * Canonical role taxonomy for the platform.
 *
 * The backend (`/auth/me/`) currently returns a free-form `role` string that
 * is only used as a display label — every authenticated account is a hostel
 * owner/staff account created via signup. This module gives that string a
 * closed vocabulary so routes, navigation and actions can be permission-gated
 * without waiting for the backend RBAC build-out.
 */
export const ROLES = [
  "SUPER_ADMIN",
  "OWNER",
  "ADMIN",
  "MANAGER",
  "RECEPTIONIST",
  "ACCOUNTANT",
  "WARDEN",
  "STAFF",
  "READ_ONLY",
  "STUDENT",
  "RESIDENT",
  "GUARDIAN",
  "PARENT",
  "GUEST",
] as const;

export type Role = (typeof ROLES)[number];

const ROLE_SET = new Set<string>(ROLES);

/**
 * Map the backend's free-form role string onto the taxonomy.
 *
 * IMPORTANT — backward compatibility: historically the app never gated
 * anything on role, and accounts created before the taxonomy existed carry
 * `role: undefined` (the UI labelled them "OWNER"). A missing or unrecognized
 * role therefore normalizes to OWNER so no existing account loses access.
 * Tighten this default only after the backend starts issuing real roles.
 */
export function normalizeRole(raw?: string | null): Role {
  const candidate = (raw || "").trim().toUpperCase().replace(/[\s-]+/g, "_");
  return (ROLE_SET.has(candidate) ? candidate : "OWNER") as Role;
}
