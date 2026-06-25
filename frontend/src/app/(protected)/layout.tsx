"use client";

import "../globals.css";
import { ReactNode, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/shared/auth/AuthProvider";
import { authStore } from "@/shared/auth/auth.store";
import { PageSkeleton } from "@/shared/ui/Skeleton";

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

  return <div className="mx-auto max-w-6xl p-4">{children}</div>;
}
