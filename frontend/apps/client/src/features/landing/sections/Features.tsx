import React from "react";
import { Section } from "../components/Section";
import { SectionHeader } from "../components/SectionHeader";
import { Reveal } from "../components/Reveal";
import { FEATURES } from "../content";
import { SECTION_IDS } from "../constants";

export function Features() {
  return (
    <Section id={SECTION_IDS.features} width="wide">
      <SectionHeader
        eyebrow="Features"
        title="Everything you need to run a hostel"
        description="One platform for admissions, occupancy, billing and compliance — so your team stops juggling tools and registers."
      />

      <ul className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map((feature, i) => {
          const Icon = feature.icon;
          return (
            <Reveal as="li" key={feature.title} delay={(i % 3) * 80}>
              <div className="group h-full rounded-2xl border border-[var(--border)] bg-[var(--card)] p-6 shadow-[var(--shadow-sm)] transition duration-200 hover:-translate-y-1 hover:border-[var(--border-hover)] hover:shadow-[var(--shadow-md)]">
                <span className="grid h-11 w-11 place-items-center rounded-xl bg-[var(--accent-soft)] text-[var(--accent)] transition group-hover:scale-105">
                  <Icon className="h-5.5 w-5.5" aria-hidden />
                </span>
                <h3 className="mt-5 text-lg font-semibold text-[var(--foreground)]">
                  {feature.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-[var(--foreground-secondary)]">
                  {feature.description}
                </p>
              </div>
            </Reveal>
          );
        })}
      </ul>
    </Section>
  );
}
