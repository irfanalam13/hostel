import React from "react";
import Link from "next/link";
import { Check } from "lucide-react";
import { Section } from "../components/Section";
import { SectionHeader } from "../components/SectionHeader";
import { Reveal } from "../components/Reveal";
import { PRICING } from "../content";
import { SECTION_IDS } from "../constants";

export function Pricing() {
  return (
    <Section id={SECTION_IDS.pricing} tone="muted" width="wide">
      <SectionHeader
        eyebrow="Pricing"
        title="Simple pricing that scales with you"
        description="Start free, upgrade when you grow. No hidden fees, cancel anytime."
      />

      <div className="mt-14 grid items-stretch gap-6 lg:grid-cols-3">
        {PRICING.map((tier, i) => {
          const isAnchor = tier.cta.href.startsWith("#");
          const CtaInner = (
            <>
              {tier.cta.label}
            </>
          );
          return (
            <Reveal key={tier.name} delay={i * 90}>
              <div
                className={`relative flex h-full flex-col rounded-2xl border p-7 shadow-[var(--shadow-sm)] ${
                  tier.featured
                    ? "border-[var(--accent)] bg-[var(--card)] ring-1 ring-[var(--accent)]"
                    : "border-[var(--border)] bg-[var(--card)]"
                }`}
              >
                {tier.featured && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-[var(--accent)] px-3 py-1 text-xs font-semibold text-white shadow-sm">
                    Most popular
                  </span>
                )}

                <h3 className="text-lg font-semibold text-[var(--foreground)]">{tier.name}</h3>
                <div className="mt-4 flex items-baseline gap-1.5">
                  <span className="text-4xl font-bold tracking-tight text-[var(--foreground)]">
                    {tier.price}
                  </span>
                  {tier.period && (
                    <span className="text-sm text-[var(--muted)]">{tier.period}</span>
                  )}
                </div>
                <p className="mt-3 text-sm text-[var(--foreground-secondary)]">{tier.description}</p>

                <ul className="mt-6 flex-1 space-y-3">
                  {tier.features.map((f) => (
                    <li key={f} className="flex items-start gap-2.5 text-sm text-[var(--foreground)]">
                      <Check className="mt-0.5 h-4.5 w-4.5 shrink-0 text-[var(--success)]" aria-hidden />
                      {f}
                    </li>
                  ))}
                </ul>

                {isAnchor ? (
                  <a
                    href={tier.cta.href}
                    className={`mt-8 inline-flex w-full items-center justify-center rounded-xl px-5 py-3 text-sm font-semibold transition ${
                      tier.featured
                        ? "bg-[var(--accent)] text-white hover:bg-[var(--accent-hover)]"
                        : "border border-[var(--border)] bg-[var(--card)] text-[var(--foreground)] hover:bg-[var(--background-secondary)]"
                    }`}
                  >
                    {CtaInner}
                  </a>
                ) : (
                  <Link
                    href={tier.cta.href}
                    className={`mt-8 inline-flex w-full items-center justify-center rounded-xl px-5 py-3 text-sm font-semibold transition ${
                      tier.featured
                        ? "bg-[var(--accent)] text-white hover:bg-[var(--accent-hover)]"
                        : "border border-[var(--border)] bg-[var(--card)] text-[var(--foreground)] hover:bg-[var(--background-secondary)]"
                    }`}
                  >
                    {CtaInner}
                  </Link>
                )}
              </div>
            </Reveal>
          );
        })}
      </div>
    </Section>
  );
}
