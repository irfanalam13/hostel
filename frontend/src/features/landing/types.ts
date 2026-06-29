import type { LucideIcon } from "lucide-react";

/** A call-to-action target. `href` reuses existing app routes where possible. */
export type CtaLink = {
  label: string;
  href: string;
  /** Visual emphasis, mapped to the shared Button variants. */
  variant?: "primary" | "secondary" | "ghost";
  external?: boolean;
};

/** A single in-page navigation entry for the landing navbar / footer. */
export type NavLink = {
  label: string;
  /** In-page anchor ("#features") or route ("/login"). */
  href: string;
};

/** Generic feature/benefit item used by feature grids and cards. */
export type FeatureItem = {
  icon: LucideIcon;
  title: string;
  description: string;
};

/** Headline statistic shown in stat strips. */
export type StatItem = {
  value: string;
  label: string;
  /** Optional numeric target for animated counters. */
  to?: number;
  suffix?: string;
};
