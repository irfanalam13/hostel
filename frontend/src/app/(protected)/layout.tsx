"use client";

import "../globals.css";
import { ReactNode, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/shared/auth/AuthProvider";
import { authStore } from "@/shared/auth/auth.store";
import { PageSkeleton } from "@/shared/ui/Skeleton";
import { SidebarProvider } from "@/shared/providers/SidebarContext";
import Sidebar from "@/shared/ui/Sidebar";
import { MobileBottomNav } from "@/shared/ui/MobileBottomNav";

export default function ProtectedLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { status, hostelCode } = useAuth();

  useEffect(() => {
    // Once the session has been validated, gate access. Using status (not a raw
    // localStorage read) avoids the flash-of-unauthorized-content and the
    // double-redirect the old layout could cause.
    if (status === "unauthenticated") {
      router.replace("/login");
      return;
    }
    if (status === "authenticated" && !hostelCode && !authStore.getHostelCode()) {
      router.replace("/select-hostel");
    }
  }, [status, hostelCode, router]);

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

  return (
    <SidebarProvider>
      <div className="flex h-screen overflow-hidden bg-[var(--background)] text-[var(--foreground)] transition-colors duration-200">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          <main className="flex-1 overflow-y-auto pb-[64px] lg:pb-0 scrollbar-thin">
            {children}
          </main>
          <MobileBottomNav />
        </div>
      </div>
    </SidebarProvider>
  );
}
