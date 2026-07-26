import React from "react";
import { Quote, Star } from "lucide-react";
import { Section } from "../components/Section";
import { SectionHeader } from "../components/SectionHeader";
import { Reveal } from "../components/Reveal";
import { ReviewForm } from "../components/ReviewForm";
import { TESTIMONIALS, type Testimonial } from "../content";
import type { TestimonialStats } from "../testimonials";
import { SECTION_IDS } from "../constants";

function Stars({ rating }: { rating: number }) {
  const r = Math.max(0, Math.min(5, Math.round(rating)));
  return (
    <div className="flex gap-0.5" aria-label={`${r} out of 5 stars`}>
      {Array.from({ length: 5 }).map((_, s) => (
        <Star
          key={s}
          className={`h-4 w-4 ${
            s < r ? "fill-[var(--warning)] text-[var(--warning)]" : "text-[var(--border-hover)]"
          }`}
          aria-hidden
        />
      ))}
    </div>
  );
}

function StatsBand({ stats }: { stats: TestimonialStats }) {
  const cells = [
    { value: `${stats.appreciation_percent}%`, label: "Would recommend" },
    { value: `${stats.rating_percent}%`, label: "Overall rating" },
    { value: stats.average_rating.toFixed(1), label: "Average score" },
    { value: `${stats.total}`, label: "Verified reviews" },
  ];
  return (
    <Reveal>
      <dl className="mx-auto mt-10 grid max-w-3xl grid-cols-2 gap-6 rounded-2xl border border-[var(--border)] bg-[var(--card)] p-6 text-center shadow-[var(--shadow-sm)] sm:grid-cols-4">
        {cells.map((c) => (
          <div key={c.label}>
            <dd className="text-3xl font-bold tracking-tight text-[var(--foreground)]">{c.value}</dd>
            <dt className="mt-1 text-xs text-[var(--muted)]">{c.label}</dt>
          </div>
        ))}
      </dl>
    </Reveal>
  );
}

export function Testimonials({
  items = TESTIMONIALS,
  stats = null,
}: {
  items?: Testimonial[];
  stats?: TestimonialStats | null;
}) {
  return (
    <Section id={SECTION_IDS.testimonials} width="wide">
      <SectionHeader
        eyebrow="Testimonials"
        title="Loved by hostel teams"
        description="Owners, wardens and finance teams who replaced spreadsheets and registers with one platform."
      />

      {/* Aggregate ratings across all approved reviews. */}
      {stats && stats.total > 0 && <StatsBand stats={stats} />}

      <ul className="mt-14 grid gap-6 md:grid-cols-3">
        {items.map((t, i) => (
          <Reveal as="li" key={`${t.name}-${i}`} delay={i * 90}>
            <figure className="flex h-full flex-col rounded-2xl border border-[var(--border)] bg-[var(--card)] p-7 shadow-[var(--shadow-sm)]">
              <Quote className="h-7 w-7 text-[var(--accent)]" aria-hidden />
              <div className="mt-3">
                <Stars rating={t.rating ?? 5} />
              </div>
              <blockquote className="mt-4 flex-1 text-pretty text-base leading-relaxed text-[var(--foreground)]">
                &ldquo;{t.quote}&rdquo;
              </blockquote>
              <figcaption className="mt-6 border-t border-[var(--border)] pt-4">
                <span className="block text-sm font-semibold text-[var(--foreground)]">{t.name}</span>
                {t.role && <span className="block text-sm text-[var(--muted)]">{t.role}</span>}
              </figcaption>
            </figure>
          </Reveal>
        ))}
      </ul>

      {/* Public review system — submissions are moderated before they appear. */}
      <ReviewForm />
    </Section>
  );
}
