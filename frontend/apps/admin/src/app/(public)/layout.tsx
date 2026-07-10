"use client";

import "../globals.css";
import { ReactNode, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@hostel/auth";

// Public pages: login / signup / forgot / reset / select-hostel. The previous
// version redirected UNauthenticated users to /login — which, since /login is
// itself public, caused a redirect loop. Correct behaviour: send ALREADY
// authenticated users to the dashboard; leave everyone else on the page.
export default function PublicLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { status, hostelCode } = useAuth();

  useEffect(() => {
    if (status === "authenticated") {
      router.replace(hostelCode ? "/dashboard" : "/select-hostel");
    }
  }, [status, hostelCode, router]);

  return <div className="mx-auto max-w-6xl p-4">{children}</div>;
}
