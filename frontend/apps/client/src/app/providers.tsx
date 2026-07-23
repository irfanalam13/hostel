"use client";

import React from "react";
import { ToastProvider, ThemeProvider } from "@hostel/ui";
import { AuthProvider } from "@hostel/auth";
import { PwaProvider } from "@hostel/pwa";

/**
 * Client (marketing) app providers. Order: Toast (outermost, so anything can
 * notify) → Auth (the landing header adapts to an existing session) → PWA
 * (install prompt / update banner on marketing pages).
 */
export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <ToastProvider>
        <AuthProvider>
          <PwaProvider>{children}</PwaProvider>
        </AuthProvider>
      </ToastProvider>
    </ThemeProvider>
  );
}
