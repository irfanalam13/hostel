"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { authStore } from "@/shared/auth/auth.store";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [status, setStatus] = useState<"checking" | "ok">("checking");

  useEffect(() => {
    const access = authStore.getAccess();
    const code = authStore.getHostelCode();

    if (!access || !code) {
      router.replace("/login");
      return;
    }

    setStatus("ok");
  }, [router]);

  if (status === "checking") {
    return (
      <div className="min-h-[60vh] grid place-items-center">
        <div className="text-sm text-gray-600">Checking session…</div>
      </div>
    );
  }

  return <>{children}</>;
}