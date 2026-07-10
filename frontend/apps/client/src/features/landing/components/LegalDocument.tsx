import React from "react";
import { Container } from "./Container";

export type LegalSection = {
  heading: string;
  /** Paragraphs of body text. */
  body: string[];
  /** Optional bullet list rendered after the paragraphs. */
  bullets?: string[];
};

function slugify(s: string) {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
}

/**
 * Renders a legal/long-form document with an anchored table of contents and
 * accessible section headings. Content is data-driven via `sections`.
 */
export function LegalDocument({ sections }: { sections: LegalSection[] }) {
  return (
    <Container width="wide" className="py-16">
      <div className="grid gap-12 lg:grid-cols-[16rem_1fr]">
        {/* Table of contents */}
        <nav aria-label="On this page" className="lg:sticky lg:top-24 lg:self-start">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
            On this page
          </p>
          <ul className="space-y-2">
            {sections.map((s) => (
              <li key={s.heading}>
                <a
                  href={`#${slugify(s.heading)}`}
                  className="text-sm text-[var(--foreground-secondary)] transition hover:text-[var(--accent)]"
                >
                  {s.heading}
                </a>
              </li>
            ))}
          </ul>
        </nav>

        {/* Body */}
        <div className="max-w-2xl">
          {sections.map((s) => (
            <section key={s.heading} id={slugify(s.heading)} className="scroll-mt-24 not-first:mt-10">
              <h2 className="text-xl font-semibold text-[var(--foreground)]">{s.heading}</h2>
              {s.body.map((p, i) => (
                <p key={i} className="mt-3 text-sm leading-relaxed text-[var(--foreground-secondary)]">
                  {p}
                </p>
              ))}
              {s.bullets ? (
                <ul className="mt-3 list-disc space-y-1.5 pl-5 text-sm leading-relaxed text-[var(--foreground-secondary)]">
                  {s.bullets.map((b) => (
                    <li key={b}>{b}</li>
                  ))}
                </ul>
              ) : null}
            </section>
          ))}
        </div>
      </div>
    </Container>
  );
}
