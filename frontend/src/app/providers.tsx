"use client";

import React from "react";
import { ToastProvider } from "@/shared/ui/toast/ToastProvider";
import { ConfirmProvider } from "@/shared/ui/ConfirmProvider";
import { AuthProvider } from "@/shared/auth/AuthProvider";
import { PwaProvider } from "@/shared/providers/PwaProvider";
import { ThemeProvider } from "@/shared/providers/ThemeContext";

/**
 * App-wide client providers. Order: Toast (outermost, so anything can notify) →
 * Confirm (modal dialogs) → Auth (session state; can surface toasts) → PWA.
 */
export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <ToastProvider>
        <ConfirmProvider>
          <AuthProvider>
            <PwaProvider>{children}</PwaProvider>
          </AuthProvider>
        </ConfirmProvider>
      </ToastProvider>
    </ThemeProvider>
  );
}
