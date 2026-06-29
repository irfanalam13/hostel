import React from "react";
import { Quote, Star } from "lucide-react";
import { Section } from "../components/Section";
import { SectionHeader } from "../components/SectionHeader";
import { Reveal } from "../components/Reveal";
import { TESTIMONIALS } from "../content";
import { SECTION_IDS } from "../constants";

export function Testimonials() {
  return (
    <Section id={SECTION_IDS.testimonials} width="wide">
      <SectionHeader
        eyebrow="Testimonials"
        title="Loved by hostel teams"
        description="Owners, wardens and finance teams who replaced spreadsheets and registers with one platform."
      />

      <ul className="mt-14 grid gap-6 md:grid-cols-3">
        {TESTIMONIALS.map((t, i) => (
          <Reveal as="li" key={t.name} delay={i * 90}>
            <figure className="flex h-full flex-col rounded-2xl border border-[var(--border)] bg-[var(--card)] p-7 shadow-[var(--shadow-sm)]">
              <Quote className="h-7 w-7 text-[var(--accent)]" aria-hidden />
              <div className="mt-3 flex gap-0.5" aria-label="5 out of 5 stars">
                {Array.from({ length: 5 }).map((_, s) => (
                  <Star key={s} className="h-4 w-4 fill-[var(--warning)] text-[var(--warning)]" aria-hidden />
                ))}
              </div>
              <blockquote className="mt-4 flex-1 text-pretty text-base leading-relaxed text-[var(--foreground)]">
                &ldquo;{t.quote}&rdquo;
              </blockquote>
              <figcaption className="mt-6 border-t border-[var(--border)] pt-4">
                <span className="block text-sm font-semibold text-[var(--foreground)]">{t.name}</span>
                <span className="block text-sm text-[var(--muted)]">{t.role}</span>
              </figcaption>
            </figure>
          </Reveal>
        ))}
      </ul>
    </Section>
  );
}
