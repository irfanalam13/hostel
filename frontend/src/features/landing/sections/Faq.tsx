import React from "react";
import { Plus } from "lucide-react";
import { Section } from "../components/Section";
import { SectionHeader } from "../components/SectionHeader";
import { Reveal } from "../components/Reveal";
import { FAQS } from "../content";
import { SECTION_IDS } from "../constants";

/**
 * Native <details>/<summary> accordion — accessible and zero-JS by default
 * (keyboard + screen-reader friendly out of the box).
 */
export function Faq() {
  return (
    <Section id={SECTION_IDS.faq} width="narrow">
      <SectionHeader
        eyebrow="FAQ"
        title="Frequently asked questions"
        description="Everything you need to know before getting started."
      />

      <div className="mt-12 space-y-3">
        {FAQS.map((faq, i) => (
          <Reveal key={faq.question} delay={(i % 3) * 60}>
            <details className="group rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5 shadow-[var(--shadow-sm)] [&_summary::-webkit-details-marker]:hidden">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-base font-semibold text-[var(--foreground)] focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color-mix(in_srgb,var(--accent)_18%,transparent)]">
                {faq.question}
                <Plus
                  className="h-5 w-5 shrink-0 text-[var(--accent)] transition-transform duration-200 group-open:rotate-45"
                  aria-hidden
                />
              </summary>
              <p className="mt-3 text-sm leading-relaxed text-[var(--foreground-secondary)]">
                {faq.answer}
              </p>
            </details>
          </Reveal>
        ))}
      </div>
    </Section>
  );
}
