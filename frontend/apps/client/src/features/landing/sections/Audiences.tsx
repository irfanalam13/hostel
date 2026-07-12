import React from "react";
import { Section } from "../components/Section";
import { SectionHeader } from "../components/SectionHeader";
import { Reveal } from "../components/Reveal";
import { AUDIENCES } from "../content";

export function Audiences() {
  return (
    <Section width="wide">
      <SectionHeader
        eyebrow="Who it's for"
        title="Built for everyone who runs a hostel"
        description="From a single private hostel to multi-campus institutions — the workflows fit how you already operate."
      />

      <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {AUDIENCES.map((item, i) => {
          const Icon = item.icon;
          return (
            <Reveal key={item.title} delay={(i % 4) * 80}>
              <div className="h-full rounded-2xl border border-[var(--border)] bg-[var(--card)] p-6 text-center shadow-[var(--shadow-sm)]">
                <span className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-[var(--accent-soft)] text-[var(--accent)]">
                  <Icon className="h-6 w-6" aria-hidden />
                </span>
                <h3 className="mt-5 text-base font-semibold text-[var(--foreground)]">
                  {item.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-[var(--foreground-secondary)]">
                  {item.description}
                </p>
              </div>
            </Reveal>
          );
        })}
      </div>
    </Section>
  );
}
