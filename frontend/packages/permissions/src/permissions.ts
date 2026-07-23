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
  "accounting:manage",
  "inventory:manage",
  "operations:manage",
  "complaints:manage",
  "communications:manage",
  "reports:view",
  "sync:view",
  "profile:view",
  "settings:manage",
  "backups:manage",
  "staff:manage",
  // AI assistant surface (chat, AI dashboard). Backend enforces the finer
  // ai.chat / ai.reports / ai.manage grants; this is the coarse UI gate.
  "ai:view",
  // Platform (Super Admin) surface: subscription/plan/feature management.
  // Granted ONLY to SUPER_ADMIN (is_superuser) — never to tenant OWNER/ADMIN.
  "platform:manage",
  // End-user portal surfaces (Prompt 02). Granted ONLY to portal roles —
  // staff/admin roles do not hold them, so /student and /parent stay
  // exclusively student/parent areas (and vice versa).
  "student-portal:view",
  "parent-portal:view",
] as const;

export type Permission = (typeof PERMISSIONS)[number];

/**
 * Every permission a tenant admin may hold — i.e. all of them EXCEPT the
 * platform (Super Admin) surface. OWNER/ADMIN get this: full access to their
 * workspace, but never to cross-tenant plan/feature management, which is
 * reserved for SUPER_ADMIN (is_superuser). This is the deliberate tightening
 * of the old OWNER `"*"` default.
 */
const TENANT_ADMIN_GRANTS: readonly Permission[] = PERMISSIONS.filter(
  (p) => p !== "platform:manage",
);

/**
 * What each role may do. `"*"` grants everything (SUPER_ADMIN only).
 *
 * OWNER/ADMIN historically held `"*"`; they now hold every permission except
 * `platform:manage`, so existing accounts keep all their workspace access while
 * the platform panel stays exclusively super-admin. End-user roles hold no
 * admin permissions — the admin app is staff-only by construction.
 */
const ROLE_GRANTS: Record<Role, readonly Permission[] | "*"> = {
  SUPER_ADMIN: "*",
  OWNER: TENANT_ADMIN_GRANTS,
  ADMIN: TENANT_ADMIN_GRANTS,
  MANAGER: [
    "dashboard:view",
    "admissions:manage",
    "students:manage",
    "residents:manage",
    "rooms:manage",
    "finance:manage",
    "accounting:manage",
    "inventory:manage",
    "operations:manage",
    "complaints:manage",
    "communications:manage",
    "reports:view",
    "sync:view",
    "profile:view",
    "settings:manage",
    "staff:manage",
    "ai:view",
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
    "ai:view",
  ],
  ACCOUNTANT: [
    "dashboard:view",
    "finance:manage",
    "accounting:manage",
    "inventory:manage",
    "reports:view",
    "sync:view",
    "profile:view",
    "ai:view",
  ],
  WARDEN: [
    "dashboard:view",
    "students:manage",
    "residents:manage",
    "rooms:manage",
    "inventory:manage",
    "operations:manage",
    "complaints:manage",
    "communications:manage",
    "sync:view",
    "profile:view",
    "ai:view",
  ],
  STAFF: [
    "dashboard:view",
    "complaints:manage",
    "communications:manage",
    "sync:view",
    "profile:view",
    "ai:view",
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

/**
 * The single source of truth for "where does an authenticated user land".
 *
 * Every post-auth redirect surface (login form, public layout, logout, the
 * admin root, the marketing navbar) MUST route through this so a session never
 * lands somewhere its role can't open. The backend's `redirect` field is
 * authoritative when present (e.g. straight from the login response); the
 * role-based `portalHomeForRole` is the client-side fallback.
 */
export function postAuthHome(role: Role, backendRedirect?: string | null): string {
  return backendRedirect || portalHomeForRole(role);
}
