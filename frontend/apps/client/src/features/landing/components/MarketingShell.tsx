import React from "react";
import { Navbar } from "../sections/Navbar";
import { Footer } from "../sections/Footer";

/**
 * Shared chrome for every marketing surface (landing + sub-pages): skip link,
 * sticky Navbar, <main> landmark, and Footer. Keeps navigation consistent
 * across the landing page and the About/Privacy/Terms/Security pages.
 */
export function MarketingShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[var(--background)]">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:rounded-xl focus:bg-[var(--accent)] focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-white"
      >
        Skip to content
      </a>

      <Navbar />
      <main id="main">{children}</main>
      <Footer />
    </div>
  );
}
