import React from "react";
import { Navbar } from "./sections/Navbar";
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
import { Footer } from "./sections/Footer";

/**
 * Full marketing landing page. Composition only — each section owns its content
 * and styling. Order is conversion-oriented: hook → proof → value → install →
 * pricing → trust → objections → convert.
 */
export function LandingPage() {
  return (
    <div className="min-h-screen bg-[var(--background)]">
      {/* Skip link for keyboard users. */}
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:rounded-xl focus:bg-[var(--accent)] focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-white"
      >
        Skip to content
      </a>

      <Navbar />

      <main id="main">
        <Hero />
        <Stats />
        <Features />
        <HowItWorks />
        <Audiences />
        <PwaSection />
        <Pricing />
        <Testimonials />
        <Compliance />
        <Faq />
        <CtaBanner />
        <Contact />
      </main>

      <Footer />
    </div>
  );
}
