import React from "react";
import { Container } from "../components/Container";
import { CtaLink } from "../components/CtaLink";
import { Logo } from "../components/Logo";
import { BRAND, FOOTER_LINKS } from "../content";

export function Footer() {
  return (
    <footer className="border-t border-[var(--border)] bg-[var(--background)]">
      <Container className="py-14">
        <div className="grid gap-10 lg:grid-cols-[1.5fr_repeat(3,1fr)]">
          <div className="max-w-xs">
            <Logo />
            <p className="mt-4 text-sm leading-relaxed text-[var(--foreground-secondary)]">
              {BRAND.description}
            </p>
          </div>

          {Object.entries(FOOTER_LINKS).map(([group, links]) => (
            <nav key={group} aria-label={group}>
              <h3 className="text-sm font-semibold text-[var(--foreground)]">{group}</h3>
              <ul className="mt-4 space-y-3">
                {links.map((link) => {
                  // CtaLink soft-navigates within this marketing zone and does a
                  // full-document jump for admin-zone routes (e.g. "/login").
                  const cls =
                    "text-sm text-[var(--foreground-secondary)] transition hover:text-[var(--accent)]";
                  return (
                    <li key={link.label}>
                      <CtaLink href={link.href} className={cls}>
                        {link.label}
                      </CtaLink>
                    </li>
                  );
                })}
              </ul>
            </nav>
          ))}
        </div>

        <div className="mt-12 flex flex-col items-center justify-between gap-4 border-t border-[var(--border)] pt-8 sm:flex-row">
          <p className="text-sm text-[var(--muted)]">
            © {BRAND.name}. All rights reserved.
          </p>
          <p className="text-sm text-[var(--muted)]">Built for hostels, schools & universities.</p>
        </div>
      </Container>
    </footer>
  );
}
