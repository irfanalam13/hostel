import React from "react";
import { ArrowRight } from "lucide-react";
import { Container } from "../components/Container";
import { CtaLink } from "../components/CtaLink";
import { Reveal } from "../components/Reveal";

export function CtaBanner() {
  return (
    <section className="py-20">
      <Container>
        <Reveal>
          <div className="relative overflow-hidden rounded-3xl bg-[var(--accent)] px-6 py-14 text-center shadow-[var(--shadow-lg)] sm:px-12">
            <div aria-hidden className="landing-cta-glow" />
            <h2 className="relative mx-auto max-w-2xl text-balance text-3xl font-bold tracking-tight text-white sm:text-4xl">
              Ready to run your hostel the modern way?
            </h2>
            <p className="relative mx-auto mt-4 max-w-xl text-pretty text-base leading-relaxed text-white/85">
              Join hostels, schools and universities streamlining operations from
              one calm, fast platform. Start free — no credit card required.
            </p>
            <div className="relative mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <CtaLink
                href="/signup"
                className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-white px-6 py-3 text-base font-semibold text-[var(--accent)] shadow-sm transition hover:bg-white/90 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-white/40 sm:w-auto"
              >
                Start free <ArrowRight className="h-4.5 w-4.5" aria-hidden />
              </CtaLink>
              <CtaLink
                href="/#contact"
                className="inline-flex w-full items-center justify-center rounded-xl border border-white/40 px-6 py-3 text-base font-semibold text-white transition hover:bg-white/10 sm:w-auto"
              >
                Talk to sales
              </CtaLink>
            </div>
          </div>
        </Reveal>
      </Container>
    </section>
  );
}
