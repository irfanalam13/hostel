// Public barrel for the landing feature.

// Layout primitives
export { Container } from "./components/Container";
export { Section } from "./components/Section";
export { SectionHeader } from "./components/SectionHeader";
export { Reveal } from "./components/Reveal";
export { AnimatedNumber } from "./components/AnimatedNumber";
export { Logo } from "./components/Logo";
export { ThemeToggle } from "./components/ThemeToggle";
export { MarketingShell } from "./components/MarketingShell";
export { PageHeader } from "./components/PageHeader";
export { LegalDocument } from "./components/LegalDocument";
export type { LegalSection } from "./components/LegalDocument";

// Hooks
export { usePlatform, manualInstallSteps, manualInstallHint } from "./hooks/usePlatform";
export type { Platform, DeviceType, OS } from "./hooks/usePlatform";

// Sections
export { Navbar } from "./sections/Navbar";
export { Hero } from "./sections/Hero";
export { Stats } from "./sections/Stats";
export { Features } from "./sections/Features";
export { HowItWorks } from "./sections/HowItWorks";
export { Audiences } from "./sections/Audiences";
export { PwaSection } from "./sections/PwaSection";
export { Pricing } from "./sections/Pricing";
export { Testimonials } from "./sections/Testimonials";
export { Compliance } from "./sections/Compliance";
export { Faq } from "./sections/Faq";
export { CtaBanner } from "./sections/CtaBanner";
export { Contact } from "./sections/Contact";
export { Footer } from "./sections/Footer";

// Composition + structured data
export { LandingPage } from "./LandingPage";
export { landingJsonLd } from "./seo";

// Types & constants
export type { CtaLink, NavLink, FeatureItem, StatItem } from "./types";
export { SECTION_IDS, NAV_LINKS, CTA } from "./constants";
