import type { Metadata } from "next";
import { LandingPage } from "@/features/landing/LandingPage";
import { buildLandingJsonLd, SITE_URL } from "@/features/landing/seo";
import { getFaqs } from "@/features/landing/site";
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

export default async function HomePage() {
  // Same fetch LandingPage uses for the FAQ section — deduped by Next within
  // this render — so the FAQ structured data tracks the live content.
  const faqs = await getFaqs();
  return (
    <>
      <script
        type="application/ld+json"
        // Structured data for rich results; content is trusted (our own backend).
        dangerouslySetInnerHTML={{ __html: JSON.stringify(buildLandingJsonLd(faqs)) }}
      />
      <LandingPage />
    </>
  );
}
