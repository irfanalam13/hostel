import React from "react";
import { Container } from "./Container";

type Props = {
  eyebrow?: string;
  title: React.ReactNode;
  description?: React.ReactNode;
  /** Optional meta line, e.g. "Last updated June 2026". */
  meta?: string;
};

/** Hero header for marketing sub-pages (About, Privacy, Terms, Security). */
export function PageHeader({ eyebrow, title, description, meta }: Props) {
  return (
    <section className="relative overflow-hidden border-b border-[var(--border)]">
      <div aria-hidden className="landing-hero-glow" />
      <Container className="py-16 text-center sm:py-20">
        {eyebrow ? (
          <p className="mb-3 text-sm font-semibold uppercase tracking-wide text-[var(--accent)]">
            {eyebrow}
          </p>
        ) : null}
        <h1 className="mx-auto max-w-3xl text-balance text-4xl font-bold tracking-tight text-[var(--foreground)] sm:text-5xl">
          {title}
        </h1>
        {description ? (
          <p className="mx-auto mt-5 max-w-2xl text-pretty text-lg leading-relaxed text-[var(--foreground-secondary)]">
            {description}
          </p>
        ) : null}
        {meta ? <p className="mt-6 text-sm text-[var(--muted)]">{meta}</p> : null}
      </Container>
    </section>
  );
}
