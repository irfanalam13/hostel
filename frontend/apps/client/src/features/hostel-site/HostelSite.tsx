/**
 * Public hostel website renderer (server component).
 *
 * Receives the workspace's *published* snapshot and renders the themed,
 * SEO-friendly one-page site: nav → sections (owner-ordered) → footer.
 * The theme is applied as CSS variables on the root wrapper, so every
 * section and the inquiry form pick up the workspace's colors — and only
 * this workspace's; nothing here reads global state.
 */
import React from "react";
import type { SitePayload } from "./api";
import {
  AboutSection,
  ContactSection,
  CustomSection,
  DiningSection,
  DownloadsSection,
  EventsSection,
  FacilitiesSection,
  FaqSection,
  GallerySection,
  HeroSection,
  NoticesSection,
  PoliciesSection,
  RoomsSection,
  StaffSection,
  StatsSection,
  TestimonialsSection,
} from "./sections";

const RADIUS: Record<string, string> = {
  none: "0px", md: "8px", lg: "14px", full: "24px",
};

const SOCIAL_LABELS: Record<string, string> = {
  facebook: "Facebook", instagram: "Instagram", linkedin: "LinkedIn",
  tiktok: "TikTok", youtube: "YouTube", x: "X", whatsapp: "WhatsApp",
};

function themeVars(theme: Record<string, unknown>): React.CSSProperties {
  const t = (k: string, fallback: string) =>
    typeof theme[k] === "string" && theme[k] ? String(theme[k]) : fallback;
  return {
    "--site-primary": t("primary_color", "#2563eb"),
    "--site-secondary": t("secondary_color", "#0f172a"),
    "--site-accent": t("accent_color", "#f59e0b"),
    "--site-radius": RADIUS[t("border_radius", "lg")] ?? RADIUS.lg,
  } as React.CSSProperties;
}

function renderSection(
  section: SitePayload["sections"][number],
  site: SitePayload,
  roomOptions: string[],
) {
  const c = section.content || {};
  switch (section.type) {
    case "hero":
      return <HeroSection content={c} hostelName={site.workspace.name} />;
    case "about":
      return <AboutSection content={c} />;
    case "stats":
      return <StatsSection content={c} />;
    case "facilities":
      return <FacilitiesSection content={c} />;
    case "amenities":
      return <FacilitiesSection content={c} id="amenities" />;
    case "rooms":
      return <RoomsSection content={c} />;
    case "gallery":
      return <GallerySection content={c} />;
    case "dining":
      return <DiningSection content={c} />;
    case "staff":
      return <StaffSection content={c} />;
    case "testimonials":
      return <TestimonialsSection content={c} />;
    case "faq":
      return <FaqSection content={c} />;
    case "notices":
      return <NoticesSection content={c} />;
    case "events":
      return <EventsSection content={c} />;
    case "downloads":
      return <DownloadsSection content={c} />;
    case "policies":
      return <PoliciesSection content={c} />;
    case "contact":
      return <ContactSection content={c} roomOptions={roomOptions} />;
    case "custom":
      return <CustomSection content={c} id={`custom-${section.id}`} />;
    default:
      return null; // unknown type from a newer registry — skip gracefully
  }
}

/* eslint-disable @next/next/no-img-element -- owner-uploaded remote assets */

export function HostelSite({ site }: { site: SitePayload }) {
  const nav = (site.navigation?.items || []).filter((i) => i.visible !== false && i.label);
  const footer = site.footer || {};
  const branding = site.branding || {};
  const socials = Object.entries(site.social || {}).filter(([, url]) => url);

  const roomsSection = site.sections.find((s) => s.type === "rooms");
  const roomOptions = (Array.isArray(roomsSection?.content?.items)
    ? (roomsSection!.content.items as { name?: string }[])
    : []
  ).map((r) => r.name || "").filter(Boolean);

  const sticky = String(site.theme?.header_style ?? "sticky") !== "static";

  return (
    <div style={themeVars(site.theme || {})} className="bg-white text-gray-900">
      {/* Scoped card style so section markup stays terse. */}
      <style>{`.site-card{background:#fff;border:1px solid rgba(0,0,0,.08);border-radius:var(--site-radius);box-shadow:0 1px 3px rgba(0,0,0,.06)}`}</style>

      {/* Navigation */}
      <header className={`${sticky ? "sticky top-0 z-40 " : ""}border-b border-black/5 bg-white/95 backdrop-blur`}>
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
          <a href="#hero" className="flex min-w-0 items-center gap-2">
            {branding.logo ? (
              <img src={branding.logo} alt="" className="h-9 w-9 rounded-lg object-contain" />
            ) : (
              <span className="grid h-9 w-9 place-items-center rounded-lg bg-[var(--site-primary)] text-lg text-white">🏨</span>
            )}
            <span className="truncate font-bold text-[var(--site-secondary)]">
              {site.workspace.name}
            </span>
          </a>
          <nav aria-label="Main" className="hidden items-center gap-5 text-sm font-medium text-gray-700 md:flex">
            {nav.map((item, i) => (
              <a key={i} href={item.href || "#"} className="hover:text-[var(--site-primary)]">
                {item.label}
              </a>
            ))}
          </nav>
          {site.navigation?.show_login !== false && (
            <a
              href="/login"
              className="shrink-0 rounded-[var(--site-radius)] bg-[var(--site-primary)] px-4 py-2 text-sm font-semibold text-white hover:opacity-90"
            >
              Sign in
            </a>
          )}
        </div>
      </header>

      {/* Sections, owner-ordered */}
      <main>
        {site.sections.map((section) => (
          <React.Fragment key={section.id}>
            {renderSection(section, site, roomOptions)}
          </React.Fragment>
        ))}
      </main>

      {/* Footer */}
      <footer className="bg-[var(--site-secondary)] py-12 text-white/80">
        <div className="mx-auto grid max-w-5xl gap-8 px-4 sm:grid-cols-3">
          <div>
            <div className="font-bold text-white">{site.workspace.name}</div>
            {footer.about_text ? (
              <p className="mt-2 whitespace-pre-line text-sm">{footer.about_text}</p>
            ) : null}
          </div>
          <div>
            <div className="text-sm font-semibold uppercase tracking-wide text-white/60">Quick links</div>
            <ul className="mt-2 space-y-1 text-sm">
              {(footer.quick_links || []).map((l, i) => (
                <li key={i}>
                  <a href={l.href || "#"} className="hover:text-white">{l.label}</a>
                </li>
              ))}
            </ul>
          </div>
          <div>
            {socials.length > 0 && (
              <>
                <div className="text-sm font-semibold uppercase tracking-wide text-white/60">Follow us</div>
                <ul className="mt-2 space-y-1 text-sm">
                  {socials.map(([key, url]) => (
                    <li key={key}>
                      <a href={url} target="_blank" rel="noopener noreferrer" className="hover:text-white">
                        {SOCIAL_LABELS[key] || key}
                      </a>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        </div>
        <div className="mx-auto mt-8 max-w-5xl border-t border-white/10 px-4 pt-6 text-center text-xs text-white/50">
          {footer.copyright || `© ${new Date().getFullYear()} ${site.workspace.name}`}
        </div>
      </footer>
    </div>
  );
}

/** Friendly full-page states for non-OK site fetches. */
export function SiteUnavailable({ kind }: { kind: "unpublished" | "not_found" | "blocked" | "error" }) {
  const copy = {
    unpublished: {
      title: "This website is offline",
      body: "The hostel has temporarily unpublished its website. Please check back later.",
    },
    not_found: {
      title: "Workspace not found",
      body: "There is no hostel at this address. Check the web address for typos.",
    },
    blocked: {
      title: "Website unavailable",
      body: "This hostel's website is currently unavailable.",
    },
    error: {
      title: "Temporarily unavailable",
      body: "We couldn't load this website right now. Please try again in a moment.",
    },
  }[kind];
  return (
    <main className="grid min-h-screen place-items-center bg-gray-50 p-6">
      <div className="max-w-md rounded-2xl border bg-white p-8 text-center shadow-sm">
        <div className="text-5xl">🏢</div>
        <h1 className="mt-3 text-xl font-bold text-gray-900">{copy.title}</h1>
        <p className="mt-2 text-sm text-gray-600">{copy.body}</p>
      </div>
    </main>
  );
}
