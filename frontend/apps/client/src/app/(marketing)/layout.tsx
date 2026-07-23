import React from "react";
import { MarketingShell } from "@/features/landing/components/MarketingShell";

/**
 * Layout for marketing sub-pages (About, Privacy, Terms, Security). Wraps them
 * in the same Navbar + Footer chrome as the landing page for full consistency.
 */
export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return <MarketingShell>{children}</MarketingShell>;
}
