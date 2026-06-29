import type { Metadata } from "next";
import { LandingPage } from "@/features/landing/LandingPage";
import { landingJsonLd, SITE_URL } from "@/features/landing/seo";
import { BRAND, HERO } from "@/features/landing/content";

export const metadata: Metadata = {
  title: `${BRAND.name} — ${BRAND.tagline}`,
  description: BRAND.description,
  alternates: { canonical: "/" },
  keywords: [
    "hostel management software",
    "hostel management system",
    "boarding school management",
    "student accommodation software",
    "hostel billing and payments",
    "room and bed occupancy",
    "PWA hostel app",
  ],
  openGraph: {
    type: "website",
    url: SITE_URL,
    title: `${BRAND.name} — ${BRAND.tagline}`,
    description: HERO.subtitle,
    siteName: BRAND.name,
  },
  twitter: {
    card: "summary_large_image",
    title: `${BRAND.name} — ${BRAND.tagline}`,
    description: HERO.subtitle,
  },
};

export default function HomePage() {
  return (
    <>
      <script
        type="application/ld+json"
        // Structured data for rich results; content is static and trusted.
        dangerouslySetInnerHTML={{ __html: JSON.stringify(landingJsonLd) }}
      />
      <LandingPage />
    </>
  );
}
