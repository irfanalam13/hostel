import type { Permission } from "./permissions";

/**
 * Admin-zone route → required permission. Longest prefix wins. Routes not
 * listed here only require an authenticated session (e.g. /profile, /sync).
 * Single source of truth: the protected layout, the sidebar, the mobile nav
 * and the command palette all resolve against this table — no hardcoded
 * per-surface route lists.
 */
const ROUTE_POLICY: ReadonlyArray<{ prefix: string; permission: Permission }> = [
  { prefix: "/dashboard", permission: "dashboard:view" },
  { prefix: "/admissions", permission: "admissions:manage" },
  { prefix: "/students", permission: "students:manage" },
  { prefix: "/residents", permission: "residents:manage" },
  { prefix: "/rooms", permission: "rooms:manage" },
  { prefix: "/finance", permission: "finance:manage" },
  { prefix: "/accounting", permission: "accounting:manage" },
  { prefix: "/inventory", permission: "inventory:manage" },
  { prefix: "/fees", permission: "finance:manage" },
  { prefix: "/payments", permission: "finance:manage" },
  { prefix: "/billing", permission: "finance:manage" },
  { prefix: "/expenses", permission: "finance:manage" },
  { prefix: "/attendance", permission: "operations:manage" },
  { prefix: "/gate", permission: "operations:manage" },
  { prefix: "/leave", permission: "operations:manage" },
  { prefix: "/visitors", permission: "operations:manage" },
  { prefix: "/vacate", permission: "operations:manage" },
  { prefix: "/complaints", permission: "complaints:manage" },
  { prefix: "/notices", permission: "communications:manage" },
  { prefix: "/notifications", permission: "communications:manage" },
  { prefix: "/reports", permission: "reports:view" },
  { prefix: "/exports", permission: "reports:view" },
  // AI assistant + AI dashboard.
  { prefix: "/ai", permission: "ai:view" },
  // Immutable, hash-chained audit trail (owners/admins).
  { prefix: "/audit", permission: "settings:manage" },
  { prefix: "/settings", permission: "settings:manage" },
  { prefix: "/backup", permission: "backups:manage" },
  // Cross-tenant hostel / plan / subscription console — a platform-operator
  // surface (not in the tenant sidebar). Super-admin only; a tenant's own plan
  // lives under Settings → Billing.
  { prefix: "/tenants", permission: "platform:manage" },
  { prefix: "/staff", permission: "staff:manage" },
  // Platform (Super Admin) subscription & plan management — super-admin only.
  { prefix: "/platform", permission: "platform:manage" },
  // End-user portals (Prompt 02): exclusively student/parent — staff and
  // admin roles hold no portal permission, so role escalation in either
  // direction is impossible at the route level.
  { prefix: "/student", permission: "student-portal:view" },
  { prefix: "/parent", permission: "parent-portal:view" },
];

export function permissionForPath(pathname: string): Permission | null {
  let match: { prefix: string; permission: Permission } | null = null;
  for (const entry of ROUTE_POLICY) {
    if (pathname === entry.prefix || pathname.startsWith(entry.prefix + "/")) {
      if (!match || entry.prefix.length > match.prefix.length) match = entry;
    }
  }
  return match ? match.permission : null;
}
