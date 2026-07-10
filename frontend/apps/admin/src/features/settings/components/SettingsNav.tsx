"use client";

import Link from "next/link";
import { SETTINGS_GROUPS, sectionHref, STATUS_META } from "../registry";

/**
 * Grouped settings navigation. Used as a sticky sidebar on desktop and inside
 * the collapsible menu on mobile.
 */
export function SettingsNav({
  active,
  onNavigate,
}: {
  active: string;
  onNavigate?: () => void;
}) {
  return (
    <nav aria-label="Settings" className="space-y-5">
      {SETTINGS_GROUPS.map((group) => (
        <div key={group.id}>
          <div className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-wider text-[var(--muted)]">
            {group.label}
          </div>
          <ul className="space-y-0.5">
            {group.sections.map((section) => {
              const Icon = section.icon;
              const isActive = active === section.id;
              return (
                <li key={section.id}>
                  <Link
                    href={sectionHref(section.id)}
                    onClick={onNavigate}
                    aria-current={isActive ? "page" : undefined}
                    title={section.description}
                    className={`group flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition ${
                      isActive
                        ? "bg-[var(--accent)] font-medium text-white shadow-sm"
                        : "text-[var(--foreground-secondary)] hover:bg-[var(--background-secondary)] hover:text-[var(--foreground)]"
                    }`}
                  >
                    <Icon className={`h-4 w-4 shrink-0 ${isActive ? "text-white" : "text-[var(--muted)]"}`} />
                    <span className="flex-1 truncate">{section.label}</span>
                    {section.status !== "ready" && !isActive ? (
                      <span
                        className="h-1.5 w-1.5 shrink-0 rounded-full"
                        style={{ backgroundColor: STATUS_META[section.status].tone }}
                        aria-hidden
                        title={STATUS_META[section.status].label}
                      />
                    ) : null}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}
