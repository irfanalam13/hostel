"use client";

import React from "react";
import { useAuth } from "@hostel/auth";
import { normalizeRole, type Role } from "./roles";
import { can, type Permission } from "./permissions";

/**
 * Permission facade over the auth session. All UI gating goes through this
 * hook so the role → permission mapping stays in one place.
 */
export function usePermissions(): {
  role: Role;
  can: (permission: Permission) => boolean;
} {
  const { user } = useAuth();
  const role = normalizeRole(user?.role);
  return {
    role,
    can: (permission: Permission) => can(role, permission),
  };
}

/**
 * Render children only when the current user holds the permission. Use for
 * buttons, menu entries and page sections; route-level gating lives in the
 * protected layout via permissionForPath.
 */
export function Guard({
  permission,
  fallback = null,
  children,
}: {
  permission: Permission;
  fallback?: React.ReactNode;
  children: React.ReactNode;
}) {
  const { can: allowed } = usePermissions();
  return <>{allowed(permission) ? children : fallback}</>;
}

/** Full-page "you don't have access" state for route-level denials. */
export function AccessDenied({ homeHref = "/dashboard" }: { homeHref?: string }) {
  return (
    <div className="grid min-h-[70vh] place-items-center px-4">
      <div className="w-full max-w-md rounded-2xl border border-[var(--border)] bg-[var(--card)] p-8 text-center shadow-sm">
        <div className="text-5xl font-bold text-[var(--muted)]">403</div>
        <h1 className="mt-2 text-lg font-semibold text-[var(--foreground)]">Access denied</h1>
        <p className="mt-1 text-sm text-[var(--muted)]">
          Your role doesn’t include access to this area. Contact your hostel
          owner or administrator if you believe this is a mistake.
        </p>
        <a
          href={homeHref}
          className="mt-6 inline-block rounded-xl bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white transition hover:opacity-90"
        >
          Go back
        </a>
      </div>
    </div>
  );
}
