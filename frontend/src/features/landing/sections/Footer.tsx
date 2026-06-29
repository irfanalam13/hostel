import React from "react";
import Link from "next/link";
import { Container } from "../components/Container";
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
                  // Hash links (e.g. "/#features") use a plain <a> so the browser
                  // resolves the anchor reliably from any page. Real routes use
                  // next/link for client-side navigation.
                  const isRoute = link.href.startsWith("/") && !link.href.includes("#");
                  const cls =
                    "text-sm text-[var(--foreground-secondary)] transition hover:text-[var(--accent)]";
                  return (
                    <li key={link.label}>
                      {isRoute ? (
                        <Link href={link.href} className={cls}>
                          {link.label}
                        </Link>
                      ) : (
                        <a href={link.href} className={cls}>
                          {link.label}
                        </a>
                      )}
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
