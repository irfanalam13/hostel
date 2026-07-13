"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Menu, X, ArrowRight, Download } from "lucide-react";
import { useAuth } from "@hostel/auth";
import { postAuthHome, usePermissions } from "@hostel/permissions";
import { usePwa } from "@hostel/pwa";
import { useToast } from "@hostel/ui";
import { Container } from "../components/Container";
import { CtaLink } from "../components/CtaLink";
import { Logo } from "../components/Logo";
import { ThemeToggle } from "../components/ThemeToggle";
import { NAV_LINKS } from "../constants";
import { BRAND } from "../content";
import { usePlatform, manualInstallHint } from "../hooks/usePlatform";

export function Navbar() {
  const { status } = useAuth();
  const { role } = usePermissions();
  // Where the "Go to dashboard" CTA sends an authenticated visitor — role-aware
  // so a signed-in student/parent lands on their own portal, not the owner
  // dashboard. Owners (the platform's primary audience) resolve to /dashboard.
  const dashboardHref = postAuthHome(role);
  const { isInstallable, isInstalled, installApp } = usePwa();
  const platform = usePlatform();
  const toast = useToast();
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const [mounted, setMounted] = useState(false);

  // Auth + PWA install state only exist on the client. Until the component has
  // mounted we render the logged-out / no-install baseline so the server HTML
  // and first client render are identical — then swap in the real state. This
  // avoids hydration mismatches (the install button would otherwise shift the
  // login link to a different DOM position between server and client).
  const authed = mounted && status === "authenticated";
  // Offer install until the app is running standalone. When the browser hasn't
  // fired beforeinstallprompt (e.g. iOS Safari, or criteria not yet met) we fall
  // back to manual instructions so the action is always discoverable.
  const showInstall = mounted && !isInstalled;

  useEffect(() => setMounted(true), []);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Lock body scroll while the mobile menu is open.
  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  const handleInstall = async () => {
    setOpen(false);
    if (isInstallable) {
      await installApp();
      return;
    }
    toast.info(manualInstallHint(platform.os), "Install the app");
  };

  return (
    <header
      className={`sticky top-0 z-50 transition-colors duration-200 ${
        scrolled
          ? "border-b border-[var(--border)] bg-[color-mix(in_srgb,var(--background)_85%,transparent)] backdrop-blur-md"
          : "border-b border-transparent"
      }`}
    >
      <Container as="nav" aria-label="Primary" className="flex h-16 items-center justify-between gap-4">
        <Link href="/" aria-label={`${BRAND.name} home`} className="shrink-0">
          <Logo />
        </Link>

        {/* Desktop links */}
        <ul className="hidden items-center gap-1 md:flex">
          {NAV_LINKS.map((link) => (
            <li key={link.href}>
              <a
                href={link.href}
                className="rounded-lg px-3 py-2 text-sm font-medium text-[var(--foreground-secondary)] transition hover:bg-[var(--background-secondary)] hover:text-[var(--foreground)]"
              >
                {link.label}
              </a>
            </li>
          ))}
        </ul>

        {/* Desktop actions */}
        <div className="hidden items-center gap-2 md:flex">
          <ThemeToggle />

          {showInstall && (
            <button
              type="button"
              onClick={handleInstall}
              className="inline-flex items-center gap-1.5 rounded-xl border border-[var(--border)] bg-[var(--card)] px-3.5 py-2 text-sm font-semibold text-[var(--foreground)] transition hover:border-[var(--border-hover)] hover:bg-[var(--background-secondary)]"
            >
              <Download className="h-4 w-4 text-[var(--accent)]" aria-hidden />
              Install app
            </button>
          )}

          {authed ? (
            <CtaLink
              href={dashboardHref}
              className="inline-flex items-center gap-1.5 rounded-xl bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-[var(--accent-hover)]"
            >
              Go to dashboard <ArrowRight className="h-4 w-4" aria-hidden />
            </CtaLink>
          ) : (
            <>
              <CtaLink
                href="/login"
                className="rounded-xl px-3 py-2 text-sm font-medium text-[var(--foreground-secondary)] transition hover:text-[var(--foreground)]"
              >
                Log in
              </CtaLink>
              <CtaLink
                href="/signup"
                className="inline-flex items-center gap-1.5 rounded-xl bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-[var(--accent-hover)]"
              >
                Get started <ArrowRight className="h-4 w-4" aria-hidden />
              </CtaLink>
            </>
          )}
        </div>

        {/* Mobile toggles */}
        <div className="flex items-center gap-2 md:hidden">
          <ThemeToggle />
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            aria-controls="mobile-menu"
            aria-label={open ? "Close menu" : "Open menu"}
            className="grid h-9 w-9 place-items-center rounded-xl border border-[var(--border)] bg-[var(--card)] text-[var(--foreground)]"
          >
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </Container>

      {/* Mobile menu */}
      {open && (
        <div id="mobile-menu" className="border-t border-[var(--border)] bg-[var(--background)] md:hidden">
          <Container className="flex flex-col gap-1 py-4">
            {NAV_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                onClick={() => setOpen(false)}
                className="rounded-lg px-3 py-3 text-base font-medium text-[var(--foreground-secondary)] transition hover:bg-[var(--background-secondary)] hover:text-[var(--foreground)]"
              >
                {link.label}
              </a>
            ))}
            <div className="mt-3 flex flex-col gap-2">
              {showInstall && (
                <button
                  type="button"
                  onClick={handleInstall}
                  className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-[var(--border)] bg-[var(--card)] px-4 py-3 text-sm font-semibold text-[var(--foreground)]"
                >
                  <Download className="h-4 w-4 text-[var(--accent)]" aria-hidden />
                  Install app
                </button>
              )}
              {authed ? (
                <CtaLink
                  href={dashboardHref}
                  onClick={() => setOpen(false)}
                  className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-[var(--accent)] px-4 py-3 text-sm font-semibold text-white"
                >
                  Go to dashboard <ArrowRight className="h-4 w-4" aria-hidden />
                </CtaLink>
              ) : (
                <>
                  <CtaLink
                    href="/login"
                    onClick={() => setOpen(false)}
                    className="inline-flex items-center justify-center rounded-xl border border-[var(--border)] bg-[var(--card)] px-4 py-3 text-sm font-semibold text-[var(--foreground)]"
                  >
                    Log in
                  </CtaLink>
                  <CtaLink
                    href="/signup"
                    onClick={() => setOpen(false)}
                    className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-[var(--accent)] px-4 py-3 text-sm font-semibold text-white"
                  >
                    Get started <ArrowRight className="h-4 w-4" aria-hidden />
                  </CtaLink>
                </>
              )}
            </div>
          </Container>
        </div>
      )}
    </header>
  );
}
