"use client";

import React from "react";
import { ToastProvider } from "@/shared/ui/toast/ToastProvider";
import { ConfirmProvider } from "@/shared/ui/ConfirmProvider";
import { AuthProvider } from "@/shared/auth/AuthProvider";

/**
 * App-wide client providers. Order: Toast (outermost, so anything can notify) →
 * Confirm (modal dialogs) → Auth (session state; can surface toasts).
 */
export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ToastProvider>
      <ConfirmProvider>
        <AuthProvider>{children}</AuthProvider>
      </ConfirmProvider>
    </ToastProvider>
  );
}
