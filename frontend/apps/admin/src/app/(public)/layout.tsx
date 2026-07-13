"use client";

import "../globals.css";
import { ReactNode, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@hostel/auth";
import { postAuthHome, usePermissions } from "@hostel/permissions";

// Public pages: login / signup / forgot / reset / select-hostel. The previous
// version redirected UNauthenticated users to /login — which, since /login is
// itself public, caused a redirect loop. Correct behaviour: send ALREADY
// authenticated users to their role's home; leave everyone else on the page.
export default function PublicLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { status, hostelCode } = useAuth();
  const { role } = usePermissions();

  useEffect(() => {
    if (status === "authenticated") {
      // Role-aware: a signed-in student/parent must land on their own portal,
      // never be bounced to the owner dashboard (which would 403). Shared with
      // the login form + guards via postAuthHome().
      router.replace(hostelCode ? postAuthHome(role) : "/select-hostel");
    }
  }, [status, hostelCode, role, router]);

  return <div className="mx-auto max-w-6xl p-4">{children}</div>;
}
