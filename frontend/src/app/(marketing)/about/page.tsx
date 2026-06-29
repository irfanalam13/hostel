import type { Metadata } from "next";
import { Target, Heart, Sparkles, ShieldCheck } from "lucide-react";
import { PageHeader } from "@/features/landing/components/PageHeader";
import { Section } from "@/features/landing/components/Section";
import { Reveal } from "@/features/landing/components/Reveal";
import { Stats } from "@/features/landing/sections/Stats";
import { Audiences } from "@/features/landing/sections/Audiences";
import { CtaBanner } from "@/features/landing/sections/CtaBanner";
import { BRAND } from "@/features/landing/content";

export const metadata: Metadata = {
  title: "About",
  description: `Learn about ${BRAND.name} — ${BRAND.tagline}. We help hostels, schools and universities run admissions, billing and occupancy from one platform.`,
  alternates: { canonical: "/about" },
};

const VALUES = [
  {
    icon: Target,
    title: "Built for operators",
    description: "Every feature comes from how hostels actually run — not how software thinks they should.",
  },
  {
    icon: Heart,
    title: "Calm by design",
    description: "A fast, uncluttered interface that reduces busywork instead of adding to it.",
  },
  {
    icon: Sparkles,
    title: "Offline-first",
    description: "Reliable even when the internet isn't — your front desk never stops working.",
  },
  {
    icon: ShieldCheck,
    title: "Secure & accountable",
    description: "Tenant isolation, role-based access and a full audit trail, out of the box.",
  },
];

export default function AboutPage() {
  return (
    <>
      <PageHeader
        eyebrow="About us"
        title="The operating system for modern hostels"
        description={`${BRAND.name} unifies admissions, beds, billing, payments and compliance so hostel teams can spend less time on paperwork and more time on people.`}
      />

      <Section width="wide">
        <div className="grid gap-10 lg:grid-cols-2 lg:gap-16">
          <Reveal>
            <div>
              <h2 className="text-2xl font-bold tracking-tight text-[var(--foreground)]">Our mission</h2>
              <p className="mt-4 text-pretty leading-relaxed text-[var(--foreground-secondary)]">
                Hostels are run on spreadsheets, register books and unreliable internet. We set out to
                replace that with a single, dependable platform — one that works on any device, even
                offline, and that any warden or finance officer can pick up in minutes.
              </p>
              <p className="mt-4 text-pretty leading-relaxed text-[var(--foreground-secondary)]">
                From a single private hostel to multi-campus institutions, our goal is the same: make
                day-to-day operations effortless and give owners a clear, real-time view of occupancy
                and collections.
              </p>
            </div>
          </Reveal>

          <div className="grid gap-4 sm:grid-cols-2">
            {VALUES.map((v, i) => {
              const Icon = v.icon;
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
        </div>
      </Section>

      <Stats />

      <Audiences />

      <CtaBanner />
    </>
  );
}
