import type { Metadata } from "next";
import { headers } from "next/headers";
import { LandingPage } from "@/features/landing/LandingPage";
import { buildLandingJsonLd, SITE_URL } from "@/features/landing/seo";
import { getFaqs } from "@/features/landing/site";
import { BRAND, HERO } from "@/features/landing/content";
import { permanentRedirect } from "next/navigation";
import { getPublicWebsite, type SiteIdentifier, type SitePayload } from "@/features/hostel-site/api";
import { HostelSite, SiteUnavailable } from "@/features/hostel-site/HostelSite";

/**
 * The root page serves two completely different experiences by host:
 *
 *  - Workspace host (everest.myhostel.com — the edge proxy stamps
 *    `x-workspace` from the Host header): the hostel's own published public
 *    website, themed and SEO'd per tenant (Website Builder, Prompt 03).
 *  - Root domain: the platform's marketing landing page, unchanged.
 */

async function siteIdentifierFromRequest(): Promise<{ id: SiteIdentifier; host: string } | null> {
  const h = await headers();
  const host = h.get("host") || "";
  const workspace = h.get("x-workspace");
  if (workspace) return { id: { workspace }, host };
  // Tenant custom domain (Prompt 05) — stamped by the edge proxy.
  const tenantHost = h.get("x-tenant-host");
  if (tenantHost) return { id: { tenantHost }, host };
  return null;
}

export async function generateMetadata(): Promise<Metadata> {
  const identified = await siteIdentifierFromRequest();
  if (identified) {
    const result = await getPublicWebsite(identified.id);
    if (result.status === "ok") {
      const site = result.site;
      const seo = site.seo || {};
      // White-label: the browser title override wins over plain SEO title.
      const title = site.white_label?.browser_title || seo.meta_title || site.workspace.name;
      const description =
        seo.meta_description || `${site.workspace.name} — rooms, facilities, pricing and contact.`;
      const ogImage = seo.og_image || site.branding?.social_image || site.branding?.cover_image || "";
      return {
        title,
        description,
        keywords: seo.keywords
          ? seo.keywords.split(",").map((k) => k.trim()).filter(Boolean)
          : undefined,
        alternates: {
          canonical: seo.canonical_url || site.workspace.public_url || site.workspace.url,
        },
        robots: seo.robots || "index, follow",
        openGraph: {
          type: "website",
          url: site.workspace.public_url || site.workspace.url,
          title,
          description,
          siteName: site.workspace.name,
          ...(ogImage ? { images: [{ url: ogImage }] } : {}),
        },
        twitter: {
          card: ogImage ? "summary_large_image" : "summary",
          title,
          description,
          ...(ogImage ? { images: [ogImage] } : {}),
        },
        ...(site.branding?.favicon ? { icons: { icon: site.branding.favicon } } : {}),
      };
    }
    // Unavailable workspace sites must never be indexed.
    return { title: "Hostel website", robots: "noindex" };
  }

  // Root domain — the platform marketing metadata (unchanged).
  return {
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
}

function buildHostelJsonLd(site: SitePayload) {
  const contact = site.sections.find((s) => s.type === "contact")?.content as
    | Record<string, string>
    | undefined;
  return {
    "@context": "https://schema.org",
    "@type": "LodgingBusiness",
    name: site.workspace.name,
    url: site.workspace.url,
    ...(site.branding?.logo ? { logo: site.branding.logo } : {}),
    ...(contact?.phone ? { telephone: contact.phone } : {}),
    ...(contact?.email ? { email: contact.email } : {}),
    ...(contact?.address ? { address: contact.address } : {}),
  };
}

export default async function HomePage() {
  const identified = await siteIdentifierFromRequest();

  if (identified) {
    const result = await getPublicWebsite(identified.id);
    if (result.status !== "ok") {
      return <SiteUnavailable kind={result.status === "blocked" ? "blocked" : result.status} />;
    }
    // SEO-preserving 301 (Prompt 05): when a primary custom domain is active
    // and this request came in on the default workspace host, the public site
    // permanently redirects there. Login/portal routes stay reachable on both
    // hosts — only the public homepage canonicalizes. Hostname comparison only
    // (ports differ in dev), and only for genuinely different hosts.
    const publicUrl = result.site.workspace.public_url;
    if (publicUrl && "workspace" in identified.id) {
      let shouldRedirect = false;
      try {
        // Malformed public_url -> serve normally rather than break the site.
        const target = new URL(publicUrl);
        const currentHost = identified.host.split(":")[0].toLowerCase();
        shouldRedirect = target.hostname.toLowerCase() !== currentHost;
      } catch {
        shouldRedirect = false;
      }
      // Outside the try: permanentRedirect() works by throwing Next's
      // control-flow error, which a catch block must never swallow.
      if (shouldRedirect) permanentRedirect(publicUrl);
    }
    return (
      <>
        <script
          type="application/ld+json"
          // Structured data for rich results; owner-authored plain text is
          // serialized through JSON.stringify (safely escaped).
          dangerouslySetInnerHTML={{ __html: JSON.stringify(buildHostelJsonLd(result.site)) }}
        />
        <HostelSite site={result.site} />
      </>
    );
  }

  // Root domain: the platform marketing page (unchanged behaviour).
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
