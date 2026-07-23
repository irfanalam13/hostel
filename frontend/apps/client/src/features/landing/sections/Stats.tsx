import React from "react";
import { Container } from "../components/Container";
import { Reveal } from "../components/Reveal";
import { AnimatedNumber } from "../components/AnimatedNumber";
import { STATS } from "../content";

export function Stats() {
  return (
    <section aria-label="Key metrics" className="border-y border-[var(--border)] bg-[var(--background-secondary)] py-12">
      <Container>
        <dl className="grid grid-cols-2 gap-8 lg:grid-cols-4">
          {STATS.map((stat, i) => (
            <Reveal as="div" key={stat.label} delay={i * 80} className="text-center">
              <dd className="text-3xl font-bold tracking-tight text-[var(--foreground)] sm:text-4xl">
                {stat.to !== undefined ? (
                  <AnimatedNumber to={stat.to} suffix={stat.suffix} />
                ) : (
                  stat.value
                )}
              </dd>
              <dt className="mt-2 text-sm text-[var(--foreground-secondary)]">{stat.label}</dt>
            </Reveal>
          ))}
        </dl>
      </Container>
    </section>
  );
}
