import React from "react";
import { Landmark, ShieldCheck } from "lucide-react";
import { Section } from "../components/Section";
import { SectionHeader } from "../components/SectionHeader";
import { Reveal } from "../components/Reveal";
import { COMPLIANCE } from "../content";

export function Compliance() {
  return (
    <Section tone="muted" width="wide">
      <div className="flex flex-col items-center">
        <span className="grid h-12 w-12 place-items-center rounded-2xl bg-[var(--accent-soft)] text-[var(--accent)]">
          <Landmark className="h-6 w-6" aria-hidden />
        </span>
      </div>
      <SectionHeader
        className="mt-5"
        eyebrow="Compliance & safety"
        title="Meet government & institutional requirements"
        description="Keep mandated records, control access, and stay inspection-ready with a complete, exportable audit trail."
      />

      <div className="mt-14 grid gap-5 sm:grid-cols-2">
        {COMPLIANCE.map((item, i) => (
          <Reveal key={item.title} delay={(i % 2) * 80}>
            <div className="flex h-full gap-4 rounded-2xl border border-[var(--border)] bg-[var(--card)] p-6 shadow-[var(--shadow-sm)]">
              <span className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[var(--accent-soft)] text-[var(--accent)]">
                <ShieldCheck className="h-5 w-5" aria-hidden />
              </span>
              <div>
                <h3 className="text-base font-semibold text-[var(--foreground)]">{item.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-[var(--foreground-secondary)]">
                  {item.description}
                </p>
              </div>
            </div>
          </Reveal>
        ))}
      </div>
    </Section>
  );
}
