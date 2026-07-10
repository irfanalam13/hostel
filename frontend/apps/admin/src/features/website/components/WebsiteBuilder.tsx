"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useToast } from "@hostel/ui";
import {
  unwrapList,
  websiteApi,
  type WebsiteInquiry,
  type WebsiteOverview,
  type WebsiteSection,
  type WebsiteSettings,
  type WebsiteVersion,
} from "../api/website.api";
import { SectionForm } from "./SectionForm";

/**
 * Settings → Website Builder — the CMS for the workspace's public website.
 *
 * Tabs: Overview (status/scores/inquiries), Sections (add/reorder/hide/
 * duplicate/edit via the schema-driven SectionForm), Theme, SEO & Social,
 * Inquiries inbox, Versions (history + rollback). The publish bar is always
 * visible: edits act on the draft; nothing reaches visitors until Publish.
 */

const card = "rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5";
const btn =
  "rounded-lg px-3 py-2 text-xs font-semibold transition disabled:opacity-50 ";
const btnPrimary = btn + "bg-[var(--accent)] text-white hover:opacity-90";
const btnGhost =
  btn + "border border-[var(--border)] text-[var(--foreground)] hover:border-[var(--accent)]";
const inputCls =
  "w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm " +
  "text-[var(--foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]";

const TABS = ["Overview", "Sections", "Theme", "SEO & Social", "Inquiries", "Versions"] as const;
type Tab = (typeof TABS)[number];

export function WebsiteBuilder() {
  const toast = useToast();
  const [tab, setTab] = useState<Tab>("Overview");
  const [settings, setSettings] = useState<WebsiteSettings | null>(null);
  const [overview, setOverview] = useState<WebsiteOverview | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    try {
      const [s, o] = await Promise.all([websiteApi.settings(), websiteApi.overview()]);
      setSettings(s);
      setOverview(o);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load the website builder.");
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function onPublish() {
    if (busy) return;
    setBusy(true);
    try {
      const res = await websiteApi.publish();
      toast.success(`Version ${res.version} is now live.`, "Website published");
      await reload();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Publish failed", "Error");
    } finally {
      setBusy(false);
    }
  }

  async function onUnpublish() {
    if (busy) return;
    setBusy(true);
    try {
      await websiteApi.unpublish();
      toast.success("Your public website is now offline.", "Unpublished");
      await reload();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Unpublish failed", "Error");
    } finally {
      setBusy(false);
    }
  }

  if (error) {
    return (
      <div className={card}>
        <p className="text-sm text-red-500">{error}</p>
        <button className={`mt-3 ${btnGhost}`} onClick={() => void reload()}>Retry</button>
      </div>
    );
  }
  if (!settings || !overview) {
    return <div className={card}><p className="text-sm text-[var(--muted)]">Loading website builder…</p></div>;
  }

  return (
    <div className="space-y-4">
      {/* Publish bar */}
      <div className={`${card} flex flex-wrap items-center justify-between gap-3`}>
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span
              className={`inline-block h-2.5 w-2.5 rounded-full ${settings.is_published ? "bg-green-500" : "bg-gray-400"}`}
            />
            <span className="text-sm font-semibold text-[var(--foreground)]">
              {settings.is_published ? `Live — version ${settings.published_version}` : "Offline (unpublished)"}
            </span>
            {overview.has_unpublished_changes && (
              <span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-xs font-semibold text-amber-600">
                Unpublished changes
              </span>
            )}
          </div>
          <a
            href={settings.workspace_url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-0.5 block truncate font-mono text-xs text-[var(--accent)] hover:underline"
          >
            {settings.workspace_url}
          </a>
        </div>
        <div className="flex gap-2">
          <a href={settings.workspace_url} target="_blank" rel="noopener noreferrer" className={btnGhost}>
            Preview ↗
          </a>
          {settings.is_published && (
            <button className={btnGhost} onClick={() => void onUnpublish()} disabled={busy}>
              Unpublish
            </button>
          )}
          <button className={btnPrimary} onClick={() => void onPublish()} disabled={busy}>
            {busy ? "Working…" : "Publish"}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-1 rounded-xl border border-[var(--border)] bg-[var(--card)] p-1">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold ${
              tab === t ? "bg-[var(--accent)] text-white" : "text-[var(--muted)] hover:text-[var(--foreground)]"
            }`}
          >
            {t}
            {t === "Inquiries" && overview.new_inquiry_count > 0 && (
              <span className="ml-1 rounded-full bg-red-500 px-1.5 text-[10px] text-white">
                {overview.new_inquiry_count}
              </span>
            )}
          </button>
        ))}
      </div>

      {tab === "Overview" && <OverviewTab overview={overview} settings={settings} />}
      {tab === "Sections" && (
        <SectionsTab settings={settings} onChanged={() => void reload()} />
      )}
      {tab === "Theme" && <ThemeTab settings={settings} onChanged={() => void reload()} />}
      {tab === "SEO & Social" && <SeoTab settings={settings} onChanged={() => void reload()} />}
      {tab === "Inquiries" && <InquiriesTab onChanged={() => void reload()} />}
      {tab === "Versions" && <VersionsTab onChanged={() => void reload()} />}
    </div>
  );
}

/* ------------------------------------------------------------------------- */
function OverviewTab({ overview, settings }: { overview: WebsiteOverview; settings: WebsiteSettings }) {
  const stats: [string, React.ReactNode][] = [
    ["Status", settings.is_published ? "Published" : "Draft only"],
    ["Live version", `v${overview.published_version}`],
    ["Last published", settings.published_at ? new Date(settings.published_at).toLocaleString() : "—"],
    ["Sections", `${overview.visible_section_count} visible / ${overview.section_count}`],
    ["SEO score", `${overview.seo_score}/100`],
    ["Inquiries", `${overview.inquiry_count} (${overview.new_inquiry_count} new)`],
    ["Versions", overview.version_count],
  ];
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <div className={card}>
        <h3 className="mb-3 text-sm font-bold text-[var(--foreground)]">Website overview</h3>
        <dl className="space-y-2">
          {stats.map(([k, v]) => (
            <div key={k} className="flex justify-between text-sm">
              <dt className="text-[var(--muted)]">{k}</dt>
              <dd className="font-medium text-[var(--foreground)]">{v}</dd>
            </div>
          ))}
        </dl>
      </div>
      <div className={card}>
        <h3 className="mb-3 text-sm font-bold text-[var(--foreground)]">Checklist</h3>
        <ul className="space-y-2 text-sm">
          {Object.entries(overview.seo_checks).map(([k, ok]) => (
            <li key={k} className="flex items-center gap-2">
              <span>{ok ? "✅" : "⚠️"}</span>
              <span className="text-[var(--muted)]">SEO: {k.replace(/_/g, " ")}</span>
            </li>
          ))}
          {overview.missing_sections.length > 0 ? (
            <li className="flex items-start gap-2">
              <span>⚠️</span>
              <span className="text-[var(--muted)]">
                Missing recommended sections: {overview.missing_sections.join(", ")}
              </span>
            </li>
          ) : (
            <li className="flex items-center gap-2">
              <span>✅</span>
              <span className="text-[var(--muted)]">All recommended sections present</span>
            </li>
          )}
        </ul>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------------- */
function SectionsTab({
  settings, onChanged,
}: { settings: WebsiteSettings; onChanged: () => void }) {
  const toast = useToast();
  const [sections, setSections] = useState<WebsiteSection[]>(settings.sections);
  const [openId, setOpenId] = useState<string | null>(null);
  const [addType, setAddType] = useState("");
  const [draft, setDraft] = useState<Record<string, unknown> | null>(null);

  useEffect(() => setSections(settings.sections), [settings.sections]);

  async function move(index: number, delta: number) {
    const to = index + delta;
    if (to < 0 || to >= sections.length) return;
    const next = [...sections];
    [next[index], next[to]] = [next[to], next[index]];
    setSections(next);
    try {
      await websiteApi.reorderSections(next.map((s) => s.id));
      onChanged();
    } catch {
      toast.error("Could not reorder sections", "Error");
      setSections(sections);
    }
  }

  async function toggleVisible(section: WebsiteSection) {
    const updated = await websiteApi.updateSection(section.id, { is_visible: !section.is_visible });
    setSections((list) => list.map((s) => (s.id === section.id ? updated : s)));
    onChanged();
  }

  async function duplicate(section: WebsiteSection) {
    await websiteApi.duplicateSection(section.id);
    toast.success("Section duplicated (added at the end).");
    onChanged();
  }

  async function remove(section: WebsiteSection) {
    await websiteApi.deleteSection(section.id);
    setSections((list) => list.filter((s) => s.id !== section.id));
    if (openId === section.id) setOpenId(null);
    onChanged();
  }

  async function add() {
    if (!addType) return;
    await websiteApi.addSection(addType);
    setAddType("");
    toast.success("Section added at the end of the page.");
    onChanged();
  }

  async function saveContent(section: WebsiteSection) {
    if (!draft) return;
    try {
      const updated = await websiteApi.updateSection(section.id, { content: draft });
      setSections((list) => list.map((s) => (s.id === section.id ? updated : s)));
      setOpenId(null);
      setDraft(null);
      toast.success("Section saved to the draft. Publish to make it live.");
      onChanged();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not save the section", "Error");
    }
  }

  return (
    <div className="space-y-3">
      {sections.map((section, i) => {
        const info = settings.section_types[section.type];
        const open = openId === section.id;
        return (
          <div key={section.id} className={card}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold text-[var(--foreground)]">
                  {info?.label || section.type}
                </span>
                {!section.is_visible && (
                  <span className="rounded-full bg-gray-500/15 px-2 py-0.5 text-[10px] font-semibold text-[var(--muted)]">
                    Hidden
                  </span>
                )}
              </div>
              <div className="flex flex-wrap gap-1.5">
                <button className={btnGhost} onClick={() => void move(i, -1)} disabled={i === 0}>↑</button>
                <button className={btnGhost} onClick={() => void move(i, 1)} disabled={i === sections.length - 1}>↓</button>
                <button className={btnGhost} onClick={() => void toggleVisible(section)}>
                  {section.is_visible ? "Hide" : "Show"}
                </button>
                <button className={btnGhost} onClick={() => void duplicate(section)}>Duplicate</button>
                <button
                  className={btnGhost}
                  onClick={() => {
                    if (open) { setOpenId(null); setDraft(null); }
                    else { setOpenId(section.id); setDraft({ ...section.content }); }
                  }}
                >
                  {open ? "Close" : "Edit"}
                </button>
                <button
                  className={btn + "border border-red-300 text-red-500 hover:bg-red-500/10"}
                  onClick={() => void remove(section)}
                >
                  Delete
                </button>
              </div>
            </div>
            {open && info && draft && (
              <div className="mt-4 border-t border-[var(--border)] pt-4">
                <SectionForm schema={info.fields} content={draft} onChange={setDraft} />
                <div className="mt-4 flex gap-2">
                  <button className={btnPrimary} onClick={() => void saveContent(section)}>
                    Save section
                  </button>
                  <button className={btnGhost} onClick={() => { setOpenId(null); setDraft(null); }}>
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        );
      })}

      <div className={`${card} flex flex-wrap items-center gap-2`}>
        <select value={addType} onChange={(e) => setAddType(e.target.value)} className={inputCls + " max-w-xs"}>
          <option value="">Add a section…</option>
          {Object.entries(settings.section_types).map(([type, info]) => (
            <option key={type} value={type}>{info.label}</option>
          ))}
        </select>
        <button className={btnPrimary} onClick={() => void add()} disabled={!addType}>
          Add section
        </button>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------------- */
function ThemeTab({ settings, onChanged }: { settings: WebsiteSettings; onChanged: () => void }) {
  const toast = useToast();
  const [theme, setTheme] = useState<Record<string, unknown>>(settings.theme);
  useEffect(() => setTheme(settings.theme), [settings.theme]);

  const set = (k: string, v: unknown) => setTheme((t) => ({ ...t, [k]: v }));

  async function save() {
    try {
      await websiteApi.updateSettings({ theme });
      toast.success("Theme saved to the draft. Publish to make it live.");
      onChanged();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not save the theme", "Error");
    }
  }

  const colors: [string, string][] = [
    ["primary_color", "Primary color"],
    ["secondary_color", "Secondary color"],
    ["accent_color", "Accent color"],
  ];

  return (
    <div className={card}>
      <h3 className="mb-4 text-sm font-bold text-[var(--foreground)]">Theme</h3>
      <div className="grid gap-4 sm:grid-cols-3">
        {colors.map(([key, lbl]) => (
          <div key={key}>
            <div className="mb-1 text-xs font-medium text-[var(--muted)]">{lbl}</div>
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={String(theme[key] || "#2563eb")}
                onChange={(e) => set(key, e.target.value)}
                className="h-9 w-12 cursor-pointer rounded border border-[var(--border)] bg-transparent"
              />
              <input className={inputCls} value={String(theme[key] || "")}
                     onChange={(e) => set(key, e.target.value)} />
            </div>
          </div>
        ))}
        <div>
          <div className="mb-1 text-xs font-medium text-[var(--muted)]">Border radius</div>
          <select className={inputCls} value={String(theme.border_radius || "lg")}
                  onChange={(e) => set("border_radius", e.target.value)}>
            {["none", "md", "lg", "full"].map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>
        <div>
          <div className="mb-1 text-xs font-medium text-[var(--muted)]">Header</div>
          <select className={inputCls} value={String(theme.header_style || "sticky")}
                  onChange={(e) => set("header_style", e.target.value)}>
            <option value="sticky">Sticky</option>
            <option value="static">Static</option>
          </select>
        </div>
      </div>

      {/* Live preview */}
      <div
        className="mt-5 rounded-xl border border-[var(--border)] p-4"
        style={{ background: String(theme.secondary_color || "#0f172a") }}
      >
        <div className="text-lg font-bold text-white">Preview headline</div>
        <p className="text-sm text-white/70">This is how your hero colors will look.</p>
        <span
          className="mt-3 inline-block rounded-lg px-4 py-2 text-sm font-semibold text-white"
          style={{ background: String(theme.primary_color || "#2563eb") }}
        >
          Primary button
        </span>
        <span
          className="ml-2 inline-block rounded-full px-3 py-1 text-xs font-bold text-white"
          style={{ background: String(theme.accent_color || "#f59e0b") }}
        >
          Accent badge
        </span>
      </div>

      <button className={`mt-4 ${btnPrimary}`} onClick={() => void save()}>Save theme</button>
    </div>
  );
}

/* ------------------------------------------------------------------------- */
function SeoTab({ settings, onChanged }: { settings: WebsiteSettings; onChanged: () => void }) {
  const toast = useToast();
  const [seo, setSeo] = useState(settings.seo);
  const [social, setSocial] = useState(settings.social);
  const [branding, setBranding] = useState(settings.branding);
  useEffect(() => { setSeo(settings.seo); setSocial(settings.social); setBranding(settings.branding); },
    [settings.seo, settings.social, settings.branding]);

  async function save() {
    try {
      await websiteApi.updateSettings({ seo, social, branding });
      toast.success("SEO, social links and branding saved to the draft.");
      onChanged();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not save", "Error");
    }
  }

  const seoFields: [string, string][] = [
    ["meta_title", "Meta title"], ["meta_description", "Meta description"],
    ["keywords", "Keywords (comma separated)"], ["og_image", "Social share image URL"],
    ["canonical_url", "Canonical URL"], ["robots", "Robots"],
  ];
  const brandFields: [string, string][] = [
    ["logo", "Logo URL"], ["favicon", "Favicon URL"], ["cover_image", "Cover image URL"],
  ];

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className={card}>
        <h3 className="mb-3 text-sm font-bold text-[var(--foreground)]">SEO</h3>
        <div className="space-y-3">
          {seoFields.map(([key, lbl]) => (
            <div key={key}>
              <div className="mb-1 text-xs font-medium text-[var(--muted)]">{lbl}</div>
              {key === "meta_description" ? (
                <textarea rows={3} className={inputCls} value={seo[key] || ""}
                          onChange={(e) => setSeo({ ...seo, [key]: e.target.value })} />
              ) : (
                <input className={inputCls} value={seo[key] || ""}
                       onChange={(e) => setSeo({ ...seo, [key]: e.target.value })} />
              )}
            </div>
          ))}
        </div>
      </div>
      <div className="space-y-4">
        <div className={card}>
          <h3 className="mb-3 text-sm font-bold text-[var(--foreground)]">Branding</h3>
          <div className="space-y-3">
            {brandFields.map(([key, lbl]) => (
              <div key={key}>
                <div className="mb-1 text-xs font-medium text-[var(--muted)]">{lbl}</div>
                <input className={inputCls} value={branding[key] || ""}
                       onChange={(e) => setBranding({ ...branding, [key]: e.target.value })} />
              </div>
            ))}
          </div>
        </div>
        <div className={card}>
          <h3 className="mb-3 text-sm font-bold text-[var(--foreground)]">Social links</h3>
          <div className="space-y-3">
            {Object.keys(settings.social).map((key) => (
              <div key={key}>
                <div className="mb-1 text-xs font-medium capitalize text-[var(--muted)]">{key}</div>
                <input className={inputCls} placeholder="https://…" value={social[key] || ""}
                       onChange={(e) => setSocial({ ...social, [key]: e.target.value })} />
              </div>
            ))}
          </div>
        </div>
        <button className={btnPrimary} onClick={() => void save()}>Save SEO & social</button>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------------- */
function InquiriesTab({ onChanged }: { onChanged: () => void }) {
  const [inquiries, setInquiries] = useState<WebsiteInquiry[] | null>(null);

  const load = useCallback(async () => {
    const data = await websiteApi.inquiries();
    setInquiries(unwrapList(data));
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function setStatus(inquiry: WebsiteInquiry, status: WebsiteInquiry["status"]) {
    await websiteApi.updateInquiry(inquiry.id, status);
    await load();
    onChanged();
  }

  if (!inquiries) return <div className={card}><p className="text-sm text-[var(--muted)]">Loading…</p></div>;
  if (!inquiries.length) {
    return (
      <div className={card}>
        <p className="text-sm text-[var(--muted)]">
          No inquiries yet. When visitors submit the inquiry form on your website, they appear here.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {inquiries.map((q) => (
        <div key={q.id} className={card}>
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <div className="text-sm font-bold text-[var(--foreground)]">
                {q.name}
                {q.status === "new" && (
                  <span className="ml-2 rounded-full bg-red-500/15 px-2 py-0.5 text-[10px] font-semibold text-red-500">
                    New
                  </span>
                )}
              </div>
              <div className="text-xs text-[var(--muted)]">
                {[q.email, q.phone, q.room_interest].filter(Boolean).join(" · ")}
                {" · "}{new Date(q.created_at).toLocaleString()}
              </div>
            </div>
            <div className="flex gap-1.5">
              {q.status !== "read" && (
                <button className={btnGhost} onClick={() => void setStatus(q, "read")}>Mark read</button>
              )}
              {q.status !== "archived" && (
                <button className={btnGhost} onClick={() => void setStatus(q, "archived")}>Archive</button>
              )}
            </div>
          </div>
          <p className="mt-2 whitespace-pre-line text-sm text-[var(--foreground)]">{q.message}</p>
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------------- */
function VersionsTab({ onChanged }: { onChanged: () => void }) {
  const toast = useToast();
  const [versions, setVersions] = useState<WebsiteVersion[] | null>(null);

  useEffect(() => {
    websiteApi.versions().then(setVersions).catch(() => setVersions([]));
  }, []);

  async function restore(number: number) {
    try {
      const res = await websiteApi.restoreVersion(number);
      toast.success(res.detail, "Draft restored");
      onChanged();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Restore failed", "Error");
    }
  }

  if (!versions) return <div className={card}><p className="text-sm text-[var(--muted)]">Loading…</p></div>;

  return (
    <div className={card}>
      <h3 className="mb-3 text-sm font-bold text-[var(--foreground)]">Version history</h3>
      <p className="mb-4 text-xs text-[var(--muted)]">
        Every publish creates a version. Restoring copies that version into your draft —
        review it, then publish to make it live again.
      </p>
      <ul className="divide-y divide-[var(--border)]">
        {versions.map((v) => (
          <li key={v.number} className="flex items-center justify-between gap-3 py-3 text-sm">
            <div>
              <span className="font-semibold text-[var(--foreground)]">v{v.number}</span>
              <span className="ml-2 text-[var(--muted)]">
                {new Date(v.created_at).toLocaleString()}
                {v.published_by ? ` · by ${v.published_by}` : ""}
                {v.note ? ` · “${v.note}”` : ""}
              </span>
            </div>
            <button className={btnGhost} onClick={() => void restore(v.number)}>
              Restore to draft
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
