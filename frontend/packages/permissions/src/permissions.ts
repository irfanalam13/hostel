import type { Role } from "./roles";

/**
 * Coarse per-module permissions (resource:action). Deliberately aligned with
 * the admin app's top-level routes so one permission gates a route, its nav
 * entry, and its command-palette entry consistently.
 */
export const PERMISSIONS = [
  "dashboard:view",
  "admissions:manage",
  "students:manage",
  "residents:manage",
  "rooms:manage",
  "finance:manage",
  "operations:manage",
  "complaints:manage",
  "communications:manage",
  "reports:view",
  "sync:view",
  "profile:view",
  "settings:manage",
  "backups:manage",
  "tenants:manage",
  // End-user portal surfaces (Prompt 02). Granted ONLY to portal roles —
  // staff/admin roles do not hold them, so /student and /parent stay
  // exclusively student/parent areas (and vice versa).
  "student-portal:view",
  "parent-portal:view",
] as const;

export type Permission = (typeof PERMISSIONS)[number];

/**
 * What each role may do. `"*"` grants everything.
 *
 * OWNER keeps `"*"` because until the backend issues differentiated roles,
 * every real account normalizes to OWNER and must keep exactly the access it
 * has today (see normalizeRole). End-user roles hold no admin permissions —
 * the admin app is staff-only by construction.
 */
const ROLE_GRANTS: Record<Role, readonly Permission[] | "*"> = {
  SUPER_ADMIN: "*",
  OWNER: "*",
  ADMIN: "*",
  MANAGER: [
    "dashboard:view",
    "admissions:manage",
    "students:manage",
    "residents:manage",
    "rooms:manage",
    "finance:manage",
    "operations:manage",
    "complaints:manage",
    "communications:manage",
    "reports:view",
    "sync:view",
    "profile:view",
    "settings:manage",
  ],
  RECEPTIONIST: [
    "dashboard:view",
    "admissions:manage",
    "students:manage",
    "residents:manage",
    "rooms:manage",
    "operations:manage",
    "complaints:manage",
    "communications:manage",
    "sync:view",
    "profile:view",
  ],
  ACCOUNTANT: [
    "dashboard:view",
    "finance:manage",
    "reports:view",
    "sync:view",
    "profile:view",
  ],
  WARDEN: [
    "dashboard:view",
    "students:manage",
    "residents:manage",
    "rooms:manage",
    "operations:manage",
    "complaints:manage",
    "communications:manage",
    "sync:view",
    "profile:view",
  ],
  STAFF: [
    "dashboard:view",
    "complaints:manage",
    "communications:manage",
    "sync:view",
    "profile:view",
  ],
  READ_ONLY: ["dashboard:view", "reports:view", "sync:view", "profile:view"],
  STUDENT: ["student-portal:view", "profile:view"],
  RESIDENT: ["student-portal:view", "profile:view"], // legacy student-equivalent
  GUARDIAN: ["parent-portal:view", "profile:view"],
  PARENT: ["parent-portal:view", "profile:view"],
  GUEST: [],
};

export function can(role: Role, permission: Permission): boolean {
  const grants = ROLE_GRANTS[role];
  if (grants === "*") return true;
  return grants.includes(permission);
}

export function grantsFor(role: Role): readonly Permission[] {
  const grants = ROLE_GRANTS[role];
  return grants === "*" ? PERMISSIONS : grants;
}

/**
 * Where a successful login should land, by role — the frontend mirror of the
 * backend's redirect rule (the login response's `redirect` field is
 * authoritative; this covers client-side fallbacks and guards).
 */
export function portalHomeForRole(role: Role): string {
  if (role === "STUDENT" || role === "RESIDENT") return "/student/dashboard";
  if (role === "PARENT" || role === "GUARDIAN") return "/parent/dashboard";
  return "/dashboard";
}
