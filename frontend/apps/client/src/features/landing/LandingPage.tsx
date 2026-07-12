import React from "react";
import { MarketingShell } from "./components/MarketingShell";
import { Hero } from "./sections/Hero";
import { Stats } from "./sections/Stats";
import { Features } from "./sections/Features";
import { HowItWorks } from "./sections/HowItWorks";
import { Audiences } from "./sections/Audiences";
import { PwaSection } from "./sections/PwaSection";
import { Pricing } from "./sections/Pricing";
import { Testimonials } from "./sections/Testimonials";
import { Compliance } from "./sections/Compliance";
import { Faq } from "./sections/Faq";
import { CtaBanner } from "./sections/CtaBanner";
import { Contact } from "./sections/Contact";
import { getPricingTiers } from "./plans";
import { getTestimonials } from "./testimonials";
import { getFaqs } from "./site";

/**
 * Full marketing landing page. Composition only — each section owns its content
 * and styling. Order is conversion-oriented: hook → proof → value → install →
 * pricing → trust → objections → convert.
 *
 * Server component: pricing and testimonials are fetched from the backend (with
 * static fallbacks) so plans, discounts and reviews stay live without a redeploy.
 */
export async function LandingPage() {
  const [pricingTiers, testimonials, faqs] = await Promise.all([
    getPricingTiers(),
    getTestimonials(),
    getFaqs(),
  ]);
  return (
    <MarketingShell>
      <Hero />
      <Stats />
      <Features />
      <HowItWorks />
      <Audiences />
      <PwaSection />
      <Pricing tiers={pricingTiers} />
      <Testimonials items={testimonials.items} stats={testimonials.stats} />
      <Compliance />
      <Faq faqs={faqs} />
      <CtaBanner />
      <Contact />
    </MarketingShell>
  );
}
