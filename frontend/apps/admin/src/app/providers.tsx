"use client";

import React from "react";
import { ToastProvider } from "@hostel/ui";
import { ConfirmProvider } from "@hostel/ui";
import { AuthProvider } from "@hostel/auth";
import { PwaProvider } from "@hostel/pwa";
import { ThemeProvider } from "@hostel/ui";

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
