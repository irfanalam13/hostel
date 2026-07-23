import React from "react";
import { Section } from "../components/Section";
import { SectionHeader } from "../components/SectionHeader";
import { Reveal } from "../components/Reveal";
import { STEPS } from "../content";

export function HowItWorks() {
  return (
    <Section tone="muted" width="wide">
      <SectionHeader
        eyebrow="How it works"
        title="Live in four simple steps"
        description="From setup to insight — no consultants, no lengthy onboarding."
      />

      <ol className="mt-14 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {STEPS.map((step, i) => (
          <Reveal as="li" key={step.title} delay={i * 80}>
            <div className="relative h-full rounded-2xl border border-[var(--border)] bg-[var(--card)] p-6 shadow-[var(--shadow-sm)]">
              <span className="grid h-10 w-10 place-items-center rounded-full bg-[var(--accent)] text-sm font-bold text-white">
                {i + 1}
              </span>
              <h3 className="mt-5 text-base font-semibold text-[var(--foreground)]">
                {step.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-[var(--foreground-secondary)]">
                {step.description}
              </p>
            </div>
          </Reveal>
        ))}
      </ol>
    </Section>
  );
}
