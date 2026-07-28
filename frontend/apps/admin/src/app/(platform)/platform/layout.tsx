"use client";

import { ReactNode } from "react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@hostel/auth";
import { PageSkeleton } from "@hostel/ui";
import { AccessDenied, portalHomeForRole, usePermissions } from "@hostel/permissions";
import { PlatformTopbar } from "@/features/platform/components/shell/PlatformTopbar";

/**
 * Super-admin surface, kept deliberately separate from the tenant admin app:
 * its own layout, its own topbar, no tenant Sidebar/MobileBottomNav. A
 * platform operator isn't a member of any hostel, so none of the tenant
 * chrome (hostel switcher, tenant nav, notifications inbox) applies here.
 */
export default function PlatformLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { status } = useAuth();
  const { can, role } = usePermissions();

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
    }
  }, [status, router]);

  if (status === "loading") {
    return (
      <div className="mx-auto max-w-6xl p-4">
        <PageSkeleton />
      </div>
    );
  }

  if (status === "unauthenticated") return null;

  if (!can("platform:manage")) {
    return <AccessDenied homeHref={portalHomeForRole(role)} />;
  }

  return (
    <div className="min-h-screen bg-[var(--background)] text-[var(--foreground)] transition-colors duration-200">
      <PlatformTopbar />
      <main>{children}</main>
    </div>
  );
}
