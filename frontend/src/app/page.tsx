"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { authStore } from "@/shared/auth/auth.store";
import { hostelStore } from "@/shared/lib/hostel";

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    const access = authStore.getAccess();
    const hostelCode = hostelStore.getCode();
    const hostelId = hostelStore.getId();

    // If not logged in
    if (!access) {
      router.replace("/login");
      return;
    }

    // Logged in but hostel not selected
    if (!hostelCode && !hostelId) {
      router.replace("/select-hostel");
      return;
    }

    // Logged in + hostel selected
    router.replace("/dashboard");
  }, [router]);

  return null;
}