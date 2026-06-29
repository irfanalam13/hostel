import type { Metadata } from "next";
import { Target, Heart, Sparkles, ShieldCheck, Building2, type LucideIcon } from "lucide-react";
import { PageHeader } from "@/features/landing/components/PageHeader";
import { Section } from "@/features/landing/components/Section";
import { Reveal } from "@/features/landing/components/Reveal";
import { Stats } from "@/features/landing/sections/Stats";
import { Audiences } from "@/features/landing/sections/Audiences";
import { CtaBanner } from "@/features/landing/sections/CtaBanner";
import { BRAND } from "@/features/landing/content";
import { getSitePage, type SitePage, type SitePageBlock } from "@/features/landing/site";

export const metadata: Metadata = {
  title: "About",
  description: `Learn about ${BRAND.name} — ${BRAND.tagline}. We help hostels, schools and universities run admissions, billing and occupancy from one platform.`,
  alternates: { canonical: "/about" },
};

// Maps the icon names stored on the backend to lucide components.
const ICONS: Record<string, LucideIcon> = { Target, Heart, Sparkles, ShieldCheck };

// Fallback used if the backend is unreachable, so /about always renders.
const STATIC_ABOUT: SitePage = {
  slug: "about",
  eyebrow: "About us",
  title: "The operating system for modern hostels",
  description: `${BRAND.name} unifies admissions, beds, billing, payments and compliance so hostel teams can spend less time on paperwork and more time on people.`,
  body: [
    {
      type: "prose",
      heading: "Our mission",
      paragraphs: [
        "Hostels are run on spreadsheets, register books and unreliable internet. We set out to replace that with a single, dependable platform — one that works on any device, even offline, and that any warden or finance officer can pick up in minutes.",
        "From a single private hostel to multi-campus institutions, our goal is the same: make day-to-day operations effortless and give owners a clear, real-time view of occupancy and collections.",
      ],
    },
    {
      type: "cards",
      items: [
        { icon: "Target", title: "Built for operators", description: "Every feature comes from how hostels actually run — not how software thinks they should." },
        { icon: "Heart", title: "Calm by design", description: "A fast, uncluttered interface that reduces busywork instead of adding to it." },
        { icon: "Sparkles", title: "Offline-first", description: "Reliable even when the internet isn't — your front desk never stops working." },
        { icon: "ShieldCheck", title: "Secure & accountable", description: "Tenant isolation, role-based access and a full audit trail, out of the box." },
      ],
    },
  ],
};

function ProseBlock({ block }: { block: Extract<SitePageBlock, { type: "prose" }> }) {
  return (
    <Reveal>
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-[var(--foreground)]">{block.heading}</h2>
        {block.paragraphs.map((p, i) => (
          <p key={i} className="mt-4 text-pretty leading-relaxed text-[var(--foreground-secondary)]">
            {p}
          </p>
        ))}
      </div>
    </Reveal>
  );
}

function CardsBlock({ block }: { block: Extract<SitePageBlock, { type: "cards" }> }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {block.items.map((v, i) => {
        const Icon = ICONS[v.icon] ?? Building2;
        return (
          <Reveal key={v.title} delay={(i % 2) * 80}>
            <div className="h-full rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5 shadow-[var(--shadow-sm)]">
              <span className="grid h-10 w-10 place-items-center rounded-xl bg-[var(--accent-soft)] text-[var(--accent)]">
                <Icon className="h-5 w-5" aria-hidden />
              </span>
              <h3 className="mt-4 text-base font-semibold text-[var(--foreground)]">{v.title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-[var(--foreground-secondary)]">
                {v.description}
              </p>
            </div>
          </Reveal>
        );
      })}
    </div>
  );
}

export default async function AboutPage() {
  const page = (await getSitePage("about")) ?? STATIC_ABOUT;
  const prose = page.body.find((b): b is Extract<SitePageBlock, { type: "prose" }> => b.type === "prose");
  const cards = page.body.find((b): b is Extract<SitePageBlock, { type: "cards" }> => b.type === "cards");

  return (
    <>
      <PageHeader eyebrow={page.eyebrow} title={page.title} description={page.description} />

      <Section width="wide">
        <div className="grid gap-10 lg:grid-cols-2 lg:gap-16">
          {prose && <ProseBlock block={prose} />}
          {cards && <CardsBlock block={cards} />}
        </div>
      </Section>

      <Stats />
      <Audiences />
      <CtaBanner />
    </>
  );
}
