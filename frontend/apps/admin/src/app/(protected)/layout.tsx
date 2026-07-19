"use client";

import "../globals.css";
import { ReactNode, useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@hostel/auth";
import { authStore } from "@hostel/auth";
import { PageSkeleton } from "@hostel/ui";
import { SidebarProvider } from "@/components/shell/SidebarContext";
import Sidebar from "@/components/shell/Sidebar";
import { MobileBottomNav } from "@/components/shell/MobileBottomNav";
import { PresenceHeartbeat } from "@/features/system/PresenceHeartbeat";
import { OpsBanner } from "@/features/opsgov/components/OpsBanner";
import { UpgradeProvider } from "@/features/subscription/UpgradeProvider";
import { trackFeature } from "@hostel/pwa";
import {
  AccessDenied,
  permissionForPath,
  portalHomeForRole,
  usePermissions,
} from "@hostel/permissions";

export default function ProtectedLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { status, hostelCode, user } = useAuth();
  const { can, role } = usePermissions();
  const mustChangePassword = status === "authenticated" && !!user?.must_change_password;

  // Feature adoption: record the top-level section on each navigation.
  useEffect(() => {
    if (status !== "authenticated" || !pathname) return;
    const feature = pathname.split("/").filter(Boolean)[0] || "dashboard";
    trackFeature(feature);
  }, [pathname, status]);

  useEffect(() => {
    // Once the session has been validated, gate access. Using status (not a raw
    // localStorage read) avoids the flash-of-unauthorized-content and the
    // double-redirect the old layout could cause.
    if (status === "unauthenticated") {
      // One unified tenant login for every role — no role-specific login pages.
      router.replace("/login");
      return;
    }
    // First-login gate: an account provisioned with a temporary/default password
    // (staff, team invite, student admission) must set a new one before it can
    // use anything. This funnels every authenticated route to /change-password
    // until the flag clears; the change-password page itself is exempt.
    if (mustChangePassword && pathname !== "/change-password") {
      router.replace("/change-password");
      return;
    }
    // The workspace selector's whole job is to establish which workspace to
    // open, so it must not itself be bounced to /select-hostel. The forced
    // change-password screen is likewise exempt.
    const needsHostel = pathname !== "/select-workspace" && pathname !== "/change-password";
    if (needsHostel && status === "authenticated" && !hostelCode && !authStore.getHostelCode()) {
      router.replace("/select-hostel");
    }
  }, [status, hostelCode, mustChangePassword, router, pathname]);

  // While validating the session, show a skeleton instead of a blank screen.
  if (status === "loading") {
    return (
      <div className="mx-auto max-w-6xl p-4">
        <PageSkeleton />
      </div>
    );
  }

  // Redirecting — don't flash protected content.
  if (status === "unauthenticated") return null;

  // Forced password change pending: don't flash the app behind the redirect.
  if (mustChangePassword && pathname !== "/change-password") {
    return (
      <div className="mx-auto max-w-6xl p-4">
        <PageSkeleton />
      </div>
    );
  }

  // Route-level RBAC: the same policy table that filters the sidebar, mobile
  // nav and command palette decides whether this role may open this route.
  const required = permissionForPath(pathname || "");
  const allowed = !required || can(required);

  return (
    <SidebarProvider>
      <PresenceHeartbeat />
      <UpgradeProvider>
        <div className="flex h-screen overflow-hidden bg-[var(--background)] text-[var(--foreground)] transition-colors duration-200">
          <Sidebar />
          <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
            <main className="flex-1 overflow-y-auto pb-[64px] lg:pb-0 scrollbar-thin">
              <OpsBanner />
              {allowed ? children : <AccessDenied homeHref={portalHomeForRole(role)} />}
            </main>
            <MobileBottomNav />
          </div>
        </div>
      </UpgradeProvider>
    </SidebarProvider>
  );
}
