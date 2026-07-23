import React from "react";
import { ArrowRight, CheckCircle2, WifiOff, ShieldCheck } from "lucide-react";
import { Container } from "../components/Container";
import { CtaLink } from "../components/CtaLink";
import { Reveal } from "../components/Reveal";
import { HERO } from "../content";

const TRUST_POINTS = [
  { icon: WifiOff, label: "Works offline" },
  { icon: ShieldCheck, label: "Secure & audited" },
  { icon: CheckCircle2, label: "No credit card to start" },
];

export function Hero() {
  return (
    <section className="relative overflow-hidden">
      {/* Decorative gradient + grid backdrop (aria-hidden, non-interactive). */}
      <div aria-hidden className="landing-hero-glow" />
      <div aria-hidden className="landing-grid-bg absolute inset-0 -z-10" />

      <Container className="py-20 text-center sm:py-28 lg:py-32">
        <Reveal>
          <span className="inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--card)] px-4 py-1.5 text-xs font-medium text-[var(--foreground-secondary)] shadow-[var(--shadow-sm)]">
            <span className="h-2 w-2 rounded-full bg-[var(--success)]" aria-hidden />
            {HERO.badge}
          </span>
        </Reveal>

        <Reveal delay={80}>
          <h1 className="mx-auto mt-6 max-w-4xl text-balance text-4xl font-bold tracking-tight text-[var(--foreground)] sm:text-5xl lg:text-6xl">
            {HERO.title}
          </h1>
        </Reveal>

        <Reveal delay={160}>
          <p className="mx-auto mt-6 max-w-2xl text-pretty text-lg leading-relaxed text-[var(--foreground-secondary)]">
            {HERO.subtitle}
          </p>
        </Reveal>

        <Reveal delay={240}>
          <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <CtaLink
              href="/signup"
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-[var(--accent)] px-6 py-3 text-base font-semibold text-white shadow-[var(--shadow-md)] transition hover:bg-[var(--accent-hover)] focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color-mix(in_srgb,var(--accent)_25%,transparent)] sm:w-auto"
            >
              Start free <ArrowRight className="h-4.5 w-4.5" aria-hidden />
            </CtaLink>
            <a
              href="#contact"
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--card)] px-6 py-3 text-base font-semibold text-[var(--foreground)] transition hover:border-[var(--border-hover)] hover:bg-[var(--background-secondary)] sm:w-auto"
            >
              Request a demo
            </a>
          </div>
        </Reveal>

        <Reveal delay={320}>
          <ul className="mt-8 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-[var(--foreground-secondary)]">
            {TRUST_POINTS.map(({ icon: Icon, label }) => (
              <li key={label} className="inline-flex items-center gap-2">
                <Icon className="h-4 w-4 text-[var(--accent)]" aria-hidden />
                {label}
              </li>
            ))}
          </ul>
        </Reveal>

        {/* Product preview placeholder — swap for a real screenshot when available. */}
        <Reveal delay={400}>
          <div className="mx-auto mt-16 max-w-5xl">
            <div className="overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--card)] shadow-[var(--shadow-lg)]">
              <div className="flex items-center gap-1.5 border-b border-[var(--border)] bg-[var(--background-secondary)] px-4 py-3">
                <span className="h-3 w-3 rounded-full bg-[var(--error)]/70" aria-hidden />
                <span className="h-3 w-3 rounded-full bg-[var(--warning)]/70" aria-hidden />
                <span className="h-3 w-3 rounded-full bg-[var(--success)]/70" aria-hidden />
                <span className="ml-3 text-xs text-[var(--muted)]">app · dashboard</span>
              </div>
              <div className="grid gap-4 p-6 sm:grid-cols-3">
                {["Occupancy", "Collections", "Active residents"].map((k, i) => (
                  <div
                    key={k}
                    className="rounded-xl border border-[var(--border)] bg-[var(--background)] p-4 text-left"
                  >
                    <p className="text-xs font-medium text-[var(--muted)]">{k}</p>
                    <p className="mt-2 text-2xl font-bold text-[var(--foreground)]">
                      {["92%", "$48.2k", "1,204"][i]}
                    </p>
                    <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-[var(--background-secondary)]">
                      <div
                        className="h-full rounded-full bg-[var(--accent)]"
                        style={{ width: ["92%", "78%", "64%"][i] }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Reveal>
      </Container>
    </section>
  );
}
