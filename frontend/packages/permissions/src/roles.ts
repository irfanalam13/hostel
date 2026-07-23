/**
 * Canonical role taxonomy for the platform.
 *
 * The backend (`/auth/me/` and every login response) now issues a real `role`
 * drawn from a fixed set (OWNER/ADMIN/MANAGER/RECEPTIONIST/ACCOUNTANT/WARDEN/
 * STAFF/STUDENT/PARENT/RESIDENT/READ_ONLY, plus a synthesized SUPER_ADMIN for
 * platform operators). This module gives that string a closed vocabulary so
 * routes, navigation and actions are permission-gated consistently. The
 * backend stays authoritative — this mirror is UX, not a security boundary.
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
 * Least-privilege fallback for a missing or unrecognized role. READ_ONLY can
 * see the dashboard/reports but cannot manage anything, so an edge-case
 * account never silently gains admin access — while still landing on a usable
 * page rather than an empty one. (The backend enforces real access regardless;
 * this only affects what the UI offers.)
 */
const FALLBACK_ROLE: Role = "READ_ONLY";

/**
 * Map the backend's role string onto the taxonomy.
 *
 * A recognized role is used as-is (case/spacing/hyphen-insensitive). Anything
 * unknown or missing normalizes to the least-privilege {@link FALLBACK_ROLE} —
 * never to an admin role. This is the deliberate tightening of the historical
 * fail-open OWNER default: the backend issues real roles now, so an unknown
 * string means misconfiguration, not "legacy owner".
 */
export function normalizeRole(raw?: string | null): Role {
  const candidate = (raw || "").trim().toUpperCase().replace(/[\s-]+/g, "_");
  return (ROLE_SET.has(candidate) ? candidate : FALLBACK_ROLE) as Role;
}
