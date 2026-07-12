/**
 * Public hostel-website section renderers.
 *
 * One presentational component per section type in the backend registry
 * (`apps/website/sections.py`). All content is owner-authored plain text
 * rendered through React (auto-escaped) — never raw HTML. Every component
 * is defensive about missing fields so a half-filled section still renders.
 */
import React from "react";
import { InquiryForm } from "./InquiryForm";

type Content = Record<string, unknown>;

const str = (v: unknown): string => (typeof v === "string" ? v : "");
const num = (v: unknown): number => (typeof v === "number" && isFinite(v) ? v : 0);
const list = (v: unknown): Content[] => (Array.isArray(v) ? (v as Content[]) : []);

function SectionShell({
  id, title, children, alt = false,
}: { id: string; title?: string; children: React.ReactNode; alt?: boolean }) {
  return (
    <section id={id} className={alt ? "bg-black/[.03] py-16" : "py-16"}>
      <div className="mx-auto max-w-5xl px-4">
        {title ? (
          <h2 className="mb-8 text-center text-3xl font-bold text-[var(--site-secondary)]">
            {title}
          </h2>
        ) : null}
        {children}
      </div>
    </section>
  );
}

/* eslint-disable @next/next/no-img-element -- owner-uploaded remote assets */

export function HeroSection({ content, hostelName }: { content: Content; hostelName: string }) {
  const buttons = list(content.buttons);
  const image = str(content.image);
  return (
    <section id="hero" className="relative overflow-hidden bg-[var(--site-secondary)] text-white">
      {image ? (
        <img src={image} alt="" className="absolute inset-0 h-full w-full object-cover opacity-30" />
      ) : null}
      <div className="relative mx-auto max-w-5xl px-4 py-24 text-center">
        {str(content.badge) ? (
          <span className="mb-4 inline-block rounded-full bg-[var(--site-accent)] px-4 py-1 text-xs font-bold uppercase tracking-wide text-white">
            {str(content.badge)}
          </span>
        ) : null}
        <h1 className="text-4xl font-extrabold sm:text-5xl">
          {str(content.headline) || hostelName}
        </h1>
        {str(content.subtitle) ? (
          <p className="mt-4 text-xl text-white/90">{str(content.subtitle)}</p>
        ) : null}
        {str(content.description) ? (
          <p className="mx-auto mt-3 max-w-2xl text-white/75">{str(content.description)}</p>
        ) : null}
        {buttons.length > 0 && (
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            {buttons.map((b, i) => (
              <a
                key={i}
                href={str(b.href) || "#"}
                className={
                  str(b.style) === "outline"
                    ? "rounded-[var(--site-radius)] border-2 border-white/80 px-6 py-3 font-semibold text-white hover:bg-white/10"
                    : "rounded-[var(--site-radius)] bg-[var(--site-primary)] px-6 py-3 font-semibold text-white hover:opacity-90"
                }
              >
                {str(b.label) || "Learn more"}
              </a>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

export function AboutSection({ content }: { content: Content }) {
  const points = list(content.why_choose_us);
  return (
    <SectionShell id="about" title={str(content.title) || "About us"}>
      <div className="grid gap-10 md:grid-cols-2">
        <div className="space-y-4 text-gray-700">
          {str(content.story) && <p className="whitespace-pre-line">{str(content.story)}</p>}
          {str(content.mission) && (
            <p className="whitespace-pre-line"><strong>Our mission:</strong> {str(content.mission)}</p>
          )}
          {str(content.vision) && (
            <p className="whitespace-pre-line"><strong>Our vision:</strong> {str(content.vision)}</p>
          )}
          {str(content.message) && (
            <blockquote className="border-l-4 border-[var(--site-primary)] pl-4 italic">
              “{str(content.message)}”
              {str(content.message_author) && (
                <footer className="mt-1 text-sm not-italic text-gray-500">
                  — {str(content.message_author)}
                </footer>
              )}
            </blockquote>
          )}
        </div>
        {points.length > 0 && (
          <div>
            <h3 className="mb-3 font-semibold text-[var(--site-secondary)]">Why choose us</h3>
            <ul className="space-y-2">
              {points.map((p, i) => (
                <li key={i} className="flex items-start gap-2 text-gray-700">
                  <span className="mt-0.5 text-[var(--site-primary)]">✓</span>
                  {str(p.point)}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </SectionShell>
  );
}

export function StatsSection({ content }: { content: Content }) {
  const items = list(content.items);
  if (!items.length) return null;
  return (
    <section id="stats" className="bg-[var(--site-primary)] py-12 text-white">
      <div className="mx-auto grid max-w-5xl grid-cols-2 gap-6 px-4 text-center sm:grid-cols-4">
        {items.map((s, i) => (
          <div key={i}>
            <div className="text-4xl font-extrabold">
              {num(s.value).toLocaleString()}{str(s.suffix)}
            </div>
            <div className="mt-1 text-sm text-white/85">{str(s.label)}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

export function FacilitiesSection({ content, id = "facilities" }: { content: Content; id?: string }) {
  const items = list(content.items);
  return (
    <SectionShell id={id} title={str(content.title) || "Facilities"} alt>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {items.map((f, i) => (
          <div key={i} className="site-card p-5 text-center">
            <div className="text-2xl">•</div>
            <div className="mt-1 font-semibold text-[var(--site-secondary)]">{str(f.name)}</div>
            {str(f.description) && <div className="mt-1 text-sm text-gray-600">{str(f.description)}</div>}
          </div>
        ))}
      </div>
    </SectionShell>
  );
}

export function RoomsSection({ content }: { content: Content }) {
  const items = list(content.items);
  return (
    <SectionShell id="rooms" title={str(content.title) || "Rooms & pricing"}>
      <div className="grid gap-6 md:grid-cols-2">
        {items.map((r, i) => (
          <div key={i} className="site-card overflow-hidden">
            {str(r.image) && (
              <img src={str(r.image)} alt={str(r.name)} loading="lazy"
                   className="h-44 w-full object-cover" />
            )}
            <div className="p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="font-bold text-[var(--site-secondary)]">{str(r.name)}</h3>
                  {num(r.capacity) > 0 && (
                    <div className="text-xs text-gray-500">Capacity: {num(r.capacity)}</div>
                  )}
                </div>
                <div className="text-right">
                  {num(r.price_monthly) > 0 && (
                    <div className="text-lg font-extrabold text-[var(--site-primary)]">
                      Rs. {num(r.price_monthly).toLocaleString()}
                    </div>
                  )}
                  <div className="text-xs text-gray-500">{str(r.price_note)}</div>
                </div>
              </div>
              {str(r.features) && (
                <p className="mt-2 whitespace-pre-line text-sm text-gray-600">{str(r.features)}</p>
              )}
              <div className="mt-3 flex items-center justify-between">
                <span className={`text-xs font-semibold ${r.available === false ? "text-red-600" : "text-green-600"}`}>
                  {r.available === false ? "Currently full" : "Available"}
                </span>
                <a href="#inquiry" className="text-sm font-semibold text-[var(--site-primary)] hover:underline">
                  Inquire →
                </a>
              </div>
            </div>
          </div>
        ))}
      </div>
    </SectionShell>
  );
}

export function GallerySection({ content }: { content: Content }) {
  const items = list(content.items).filter((g) => str(g.image));
  if (!items.length) return null;
  return (
    <SectionShell id="gallery" title={str(content.title) || "Gallery"} alt>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
        {items.map((g, i) => (
          <figure key={i} className="overflow-hidden rounded-[var(--site-radius)]">
            <img src={str(g.image)} alt={str(g.caption) || "Gallery photo"} loading="lazy"
                 className="h-44 w-full object-cover transition hover:scale-105" />
            {str(g.caption) && (
              <figcaption className="p-1 text-center text-xs text-gray-500">{str(g.caption)}</figcaption>
            )}
          </figure>
        ))}
      </div>
    </SectionShell>
  );
}

export function DiningSection({ content }: { content: Content }) {
  const meals = list(content.meals);
  return (
    <SectionShell id="dining" title={str(content.title) || "Food & dining"}>
      {str(content.description) && (
        <p className="mx-auto mb-8 max-w-2xl whitespace-pre-line text-center text-gray-600">
          {str(content.description)}
        </p>
      )}
      <div className="grid gap-4 sm:grid-cols-3">
        {meals.map((m, i) => (
          <div key={i} className="site-card p-5 text-center">
            <div className="font-bold text-[var(--site-secondary)]">{str(m.meal)}</div>
            <div className="text-sm text-[var(--site-primary)]">{str(m.time)}</div>
            {str(m.menu) && <div className="mt-1 text-sm text-gray-600">{str(m.menu)}</div>}
          </div>
        ))}
      </div>
    </SectionShell>
  );
}

export function StaffSection({ content }: { content: Content }) {
  const items = list(content.items);
  if (!items.length) return null;
  return (
    <SectionShell id="staff" title={str(content.title) || "Our team"} alt>
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {items.map((m, i) => (
          <div key={i} className="site-card p-5 text-center">
            {str(m.photo) ? (
              <img src={str(m.photo)} alt={str(m.name)} loading="lazy"
                   className="mx-auto h-20 w-20 rounded-full object-cover" />
            ) : (
              <div className="mx-auto grid h-20 w-20 place-items-center rounded-full bg-gray-100 text-2xl">👤</div>
            )}
            <div className="mt-3 font-semibold text-[var(--site-secondary)]">{str(m.name)}</div>
            <div className="text-xs text-[var(--site-primary)]">{str(m.position)}</div>
            {str(m.description) && <p className="mt-1 text-xs text-gray-600">{str(m.description)}</p>}
          </div>
        ))}
      </div>
    </SectionShell>
  );
}

export function TestimonialsSection({ content }: { content: Content }) {
  const items = list(content.items);
  if (!items.length) return null;
  return (
    <SectionShell id="testimonials" title={str(content.title) || "What residents say"}>
      <div className="grid gap-4 md:grid-cols-3">
        {items.map((t, i) => (
          <figure key={i} className="site-card p-5">
            <div aria-label={`${num(t.rating) || 5} out of 5 stars`} className="text-[var(--site-accent)]">
              {"★".repeat(Math.min(Math.max(num(t.rating) || 5, 1), 5))}
            </div>
            <blockquote className="mt-2 text-sm text-gray-700">“{str(t.feedback)}”</blockquote>
            <figcaption className="mt-3 text-sm font-semibold text-[var(--site-secondary)]">
              {str(t.name)}
              {str(t.role) && <span className="font-normal text-gray-500"> · {str(t.role)}</span>}
            </figcaption>
          </figure>
        ))}
      </div>
    </SectionShell>
  );
}

export function FaqSection({ content }: { content: Content }) {
  const items = list(content.items);
  if (!items.length) return null;
  return (
    <SectionShell id="faq" title={str(content.title) || "Frequently asked questions"} alt>
      <div className="mx-auto max-w-3xl space-y-3">
        {items.map((f, i) => (
          <details key={i} className="site-card group p-4">
            <summary className="cursor-pointer list-none font-semibold text-[var(--site-secondary)]">
              {str(f.question)}
            </summary>
            <p className="mt-2 whitespace-pre-line text-sm text-gray-600">{str(f.answer)}</p>
          </details>
        ))}
      </div>
    </SectionShell>
  );
}

export function NoticesSection({ content }: { content: Content }) {
  const items = list(content.items);
  if (!items.length) return null;
  return (
    <SectionShell id="notices" title={str(content.title) || "Notices"}>
      <div className="mx-auto max-w-3xl space-y-3">
        {items.map((n, i) => (
          <div key={i} className="site-card p-4">
            <div className="flex items-center justify-between gap-3">
              <h3 className="font-semibold text-[var(--site-secondary)]">{str(n.title)}</h3>
              {str(n.date) && <span className="text-xs text-gray-500">{str(n.date)}</span>}
            </div>
            {str(n.body) && <p className="mt-1 whitespace-pre-line text-sm text-gray-600">{str(n.body)}</p>}
          </div>
        ))}
      </div>
    </SectionShell>
  );
}

export function EventsSection({ content }: { content: Content }) {
  const items = list(content.items);
  if (!items.length) return null;
  return (
    <SectionShell id="events" title={str(content.title) || "Events"} alt>
      <div className="grid gap-4 md:grid-cols-2">
        {items.map((ev, i) => (
          <div key={i} className="site-card overflow-hidden">
            {str(ev.image) && (
              <img src={str(ev.image)} alt={str(ev.name)} loading="lazy" className="h-40 w-full object-cover" />
            )}
            <div className="p-5">
              <div className="flex items-center justify-between gap-3">
                <h3 className="font-semibold text-[var(--site-secondary)]">{str(ev.name)}</h3>
                {str(ev.date) && <span className="text-xs text-gray-500">{str(ev.date)}</span>}
              </div>
              {str(ev.description) && (
                <p className="mt-1 whitespace-pre-line text-sm text-gray-600">{str(ev.description)}</p>
              )}
              {str(ev.registration_url) && (
                <a href={str(ev.registration_url)} className="mt-2 inline-block text-sm font-semibold text-[var(--site-primary)] hover:underline">
                  Register →
                </a>
              )}
            </div>
          </div>
        ))}
      </div>
    </SectionShell>
  );
}

export function DownloadsSection({ content }: { content: Content }) {
  const items = list(content.items).filter((d) => str(d.file));
  if (!items.length) return null;
  return (
    <SectionShell id="downloads" title={str(content.title) || "Downloads"}>
      <div className="mx-auto flex max-w-2xl flex-wrap justify-center gap-3">
        {items.map((d, i) => (
          <a key={i} href={str(d.file)} target="_blank" rel="noopener noreferrer"
             className="site-card px-5 py-3 text-sm font-semibold text-[var(--site-primary)] hover:underline">
            📄 {str(d.label) || "Download"}
          </a>
        ))}
      </div>
    </SectionShell>
  );
}

export function PoliciesSection({ content }: { content: Content }) {
  const items = list(content.items).filter((p) => str(p.body));
  if (!items.length) return null;
  return (
    <SectionShell id="policies" title={str(content.title) || "Policies"} alt>
      <div className="mx-auto max-w-3xl space-y-3">
        {items.map((p, i) => (
          <details key={i} className="site-card p-4">
            <summary className="cursor-pointer list-none font-semibold text-[var(--site-secondary)]">
              {str(p.name)}
            </summary>
            <p className="mt-2 whitespace-pre-line text-sm text-gray-600">{str(p.body)}</p>
          </details>
        ))}
      </div>
    </SectionShell>
  );
}

export function ContactSection({ content, roomOptions }: { content: Content; roomOptions: string[] }) {
  const rows: [string, string][] = [
    ["Phone", str(content.phone)],
    ["Email", str(content.email)],
    ["Address", str(content.address)],
    ["Office hours", str(content.office_hours)],
    ["Emergency", str(content.emergency_contact)],
  ];
  const lat = str(content.latitude);
  const lng = str(content.longitude);
  const directions = lat && lng
    ? `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(`${lat},${lng}`)}`
    : "";
  return (
    <SectionShell id="contact" title={str(content.title) || "Contact us"}>
      <div className="grid gap-10 md:grid-cols-2">
        <div>
          <dl className="space-y-3">
            {rows.filter(([, v]) => v).map(([k, v]) => (
              <div key={k} className="flex gap-3 text-sm">
                <dt className="w-28 shrink-0 font-semibold text-[var(--site-secondary)]">{k}</dt>
                <dd className="text-gray-700">{v}</dd>
              </div>
            ))}
          </dl>
          {directions && (
            <a href={directions} target="_blank" rel="noopener noreferrer"
               className="mt-4 inline-block rounded-[var(--site-radius)] border border-[var(--site-primary)] px-4 py-2 text-sm font-semibold text-[var(--site-primary)] hover:bg-[var(--site-primary)] hover:text-white">
              Get directions
            </a>
          )}
          {str(content.map_embed_url) && (
            <iframe
              src={str(content.map_embed_url)}
              title="Map"
              loading="lazy"
              className="mt-4 h-56 w-full rounded-[var(--site-radius)] border-0"
              referrerPolicy="no-referrer-when-downgrade"
            />
          )}
        </div>
        {content.show_inquiry_form !== false && (
          <div id="inquiry">
            <h3 className="mb-3 font-semibold text-[var(--site-secondary)]">Send us an inquiry</h3>
            <InquiryForm roomOptions={roomOptions} />
          </div>
        )}
      </div>
    </SectionShell>
  );
}

export function CustomSection({ content, id }: { content: Content; id: string }) {
  if (!str(content.title) && !str(content.body)) return null;
  return (
    <SectionShell id={id} title={str(content.title)}>
      {str(content.image) && (
        <img src={str(content.image)} alt="" loading="lazy"
             className="mx-auto mb-6 max-h-80 rounded-[var(--site-radius)] object-cover" />
      )}
      <p className="mx-auto max-w-3xl whitespace-pre-line text-gray-700">{str(content.body)}</p>
    </SectionShell>
  );
}
