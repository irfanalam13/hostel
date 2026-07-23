"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ChevronRight, Menu, X } from "lucide-react";
import { Topbar } from "@/components/shell/Topbar";
import { findSection, groupForSection } from "../registry";
import { SettingsNav } from "./SettingsNav";
import { SettingsSearch } from "./SettingsSearch";
import { SettingsHome } from "./SettingsHome";
import { PlaceholderSection } from "./primitives";
import { GeneralSection } from "./sections/GeneralSection";
import { AppearanceSection } from "./sections/AppearanceSection";
import { SystemSection, AboutSection, StorageSection, BackupsSection, DataManagementSection } from "./sections/InfraSections";
import { AuditSection, BillingSettingsSection } from "./sections/ReusedSections";
import { WebsiteBuilder } from "@/features/website/components/WebsiteBuilder";
import {
  DangerZoneSection,
  TeamSection,
  WorkspaceActivitySection,
  WorkspaceBrandingSection,
  WorkspaceNotificationsSection,
  WorkspaceOverviewSection,
  WorkspacePreferencesSection,
  WorkspaceProfileSection,
  WorkspaceSecuritySection,
  WorkspaceUrlSection,
} from "@/features/workspace/components/WorkspaceSections";
import { CustomDomainsSection } from "@/features/domains/components/CustomDomainsSection";

/** Map a section id to its live content; falls back to the roadmap placeholder. */
function SectionContent({ id }: { id: string }) {
  const section = findSection(id);
  if (!section) {
    return (
      <div className="rounded-[20px] border border-dashed border-[var(--border)] bg-[var(--card)] px-6 py-16 text-center">
        <p className="text-sm font-semibold text-[var(--foreground)]">Setting not found</p>
        <p className="mt-1 text-sm text-[var(--muted)]">This settings page doesn&apos;t exist.</p>
        <Link href="/settings" className="mt-3 inline-block text-sm font-medium text-[var(--accent)] hover:underline">
          Back to settings
        </Link>
      </div>
    );
  }

  switch (section.id) {
    case "home":
      return <SettingsHome />;
    case "general":
      return <GeneralSection />;
    case "website":
      return <WebsiteBuilder />;
    case "workspace-overview":
      return <WorkspaceOverviewSection />;
    case "profile":
      return <WorkspaceProfileSection />;
    case "branding":
      return <WorkspaceBrandingSection />;
    case "workspace-url":
      return <WorkspaceUrlSection />;
    case "custom-domains":
      return <CustomDomainsSection />;
    case "preferences":
      return <WorkspacePreferencesSection />;
    case "team":
      return <TeamSection />;
    case "notifications":
      return <WorkspaceNotificationsSection />;
    case "security":
      return <WorkspaceSecuritySection />;
    case "activity":
      return <WorkspaceActivitySection />;
    case "danger":
      return <DangerZoneSection />;
    case "appearance":
      return <AppearanceSection />;
    case "audit":
      return <AuditSection />;
    case "billing":
      return <BillingSettingsSection />;
    case "backups":
      return <BackupsSection />;
    case "storage":
      return <StorageSection />;
    case "data":
      return <DataManagementSection />;
    case "system":
      return <SystemSection />;
    case "about":
      return <AboutSection />;
    default:
      return <PlaceholderSection section={section} />;
  }
}

export function SettingsShell({ section: sectionId }: { section: string }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const section = findSection(sectionId);
  const group = section ? groupForSection(section.id) : null;
  const isHome = section?.id === "home";

  // Collapse the mobile menu whenever the active section changes.
  useEffect(() => {
    setMenuOpen(false);
  }, [sectionId]);

  return (
    <div className="space-y-5">
      <Topbar title="Settings" />

      {/* Breadcrumb */}
      <nav className="flex items-center gap-1.5 text-sm text-[var(--muted)]" aria-label="Breadcrumb">
        <Link href="/settings" className="hover:text-[var(--foreground)]">
          Settings
        </Link>
        {section && !isHome ? (
          <>
            {group ? (
              <>
                <ChevronRight className="h-3.5 w-3.5" />
                <span>{group.label}</span>
              </>
            ) : null}
            <ChevronRight className="h-3.5 w-3.5" />
            <span className="font-medium text-[var(--foreground)]">{section.label}</span>
          </>
        ) : null}
      </nav>

      {/* Search + mobile menu toggle */}
      <div className="flex items-center gap-2">
        <div className="flex-1">
          <SettingsSearch />
        </div>
        <button
          type="button"
          onClick={() => setMenuOpen((v) => !v)}
          aria-expanded={menuOpen}
          aria-label="Toggle settings menu"
          className="grid h-11 w-11 shrink-0 place-items-center rounded-xl border border-[var(--border)] bg-[var(--card)] text-[var(--foreground-secondary)] shadow-[var(--shadow-sm)] transition hover:bg-[var(--background-secondary)] lg:hidden"
        >
          {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {/* Mobile nav panel */}
      {menuOpen ? (
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-4 shadow-[var(--shadow-sm)] lg:hidden">
          <SettingsNav active={section?.id ?? "home"} onNavigate={() => setMenuOpen(false)} />
        </div>
      ) : null}

      {/* Two-column layout */}
      <div className="grid gap-6 lg:grid-cols-[248px_minmax(0,1fr)]">
        <aside className="hidden lg:block">
          <div className="sticky top-[84px] max-h-[calc(100vh-104px)] overflow-y-auto pr-1">
            <SettingsNav active={section?.id ?? "home"} />
          </div>
        </aside>

        <main className="min-w-0">
          <SectionContent id={sectionId} />
        </main>
      </div>
    </div>
  );
}
