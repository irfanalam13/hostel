import type { CtaLink, NavLink } from "./types";

/**
 * In-page section anchors. Sections register these ids via <Section id=...>.
 * Kept central so navbar, footer, and skip-links stay in sync.
 */
export const SECTION_IDS = {
  features: "features",
  pricing: "pricing",
  testimonials: "testimonials",
  faq: "faq",
  contact: "contact",
} as const;

/**
 * Primary navbar links. Root-relative (`/#section`) so they resolve to the
 * landing sections from ANY page (e.g. /about), not just the landing route.
 */
export const NAV_LINKS: NavLink[] = [
  { label: "Features", href: `/#${SECTION_IDS.features}` },
  { label: "Pricing", href: `/#${SECTION_IDS.pricing}` },
  { label: "Testimonials", href: `/#${SECTION_IDS.testimonials}` },
  { label: "FAQ", href: `/#${SECTION_IDS.faq}` },
];

/**
 * Conversion CTAs. These reuse the EXISTING app routes — no new auth or
 * business logic is created for the landing page.
 */
export const CTA = {
  login: { label: "Log in", href: "/login", variant: "ghost" },
  signup: { label: "Get started", href: "/signup", variant: "primary" },
  demo: { label: "Request a demo", href: `/#${SECTION_IDS.contact}`, variant: "secondary" },
} as const satisfies Record<string, CtaLink>;
