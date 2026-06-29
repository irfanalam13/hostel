import { BRAND, FAQS, type Faq } from "./content";

/** Canonical site URL. Override via NEXT_PUBLIC_SITE_URL in the environment. */
export const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "") || "https://hostelsaas.app";

/**
 * JSON-LD structured data for the landing page: Organization + SoftwareApplication
 * + FAQPage. Rendered as a <script type="application/ld+json"> in the page. The
 * FAQ entries are passed in (backend-driven) so the structured data tracks the
 * live FAQ content; falls back to the static list.
 */
export function buildLandingJsonLd(faqs: Faq[] = FAQS) {
  return {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Organization",
        "@id": `${SITE_URL}/#organization`,
        name: BRAND.name,
        url: SITE_URL,
        description: BRAND.description,
      },
      {
        "@type": "WebSite",
        "@id": `${SITE_URL}/#website`,
        url: SITE_URL,
        name: BRAND.name,
        publisher: { "@id": `${SITE_URL}/#organization` },
      },
      {
        "@type": "SoftwareApplication",
        name: BRAND.name,
        applicationCategory: "BusinessApplication",
        operatingSystem: "Web, iOS, Android",
        description: BRAND.description,
        offers: {
          "@type": "Offer",
          price: "0",
          priceCurrency: "USD",
          description: "Free plan available",
        },
      },
      {
        "@type": "FAQPage",
        mainEntity: (faqs.length ? faqs : FAQS).map((f) => ({
          "@type": "Question",
          name: f.question,
          acceptedAnswer: { "@type": "Answer", text: f.answer },
        })),
      },
    ],
  };
}

/** Static default (used where a synchronous value is needed). */
export const landingJsonLd = buildLandingJsonLd();
