"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Server,
  Info,
  HardDrive,
  DatabaseBackup,
  Archive,
  ArrowRight,
  Wifi,
  WifiOff,
  ShieldCheck,
  RefreshCw,
} from "lucide-react";
import { API_BASE } from "@hostel/api";
import { Button } from "@hostel/ui";
import { StorageCard } from "@hostel/pwa";
import { SectionHeader, SettingsPanel, DetailRow } from "../primitives";

const APP_VERSION = process.env.NEXT_PUBLIC_APP_VERSION || "0.1.0";

function useRuntimeInfo() {
  const [online, setOnline] = useState(true);
  const [swActive, setSwActive] = useState(false);

  useEffect(() => {
    setOnline(navigator.onLine);
    setSwActive(!!navigator.serviceWorker?.controller);
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);

  return { online, swActive };
}

export function SystemSection() {
  const { online, swActive } = useRuntimeInfo();
  const environment = process.env.NODE_ENV || "production";
  let apiHost = API_BASE;
  try {
    apiHost = new URL(API_BASE).host;
  } catch {
    /* keep raw value */
  }

  return (
    <div className="space-y-5">
      <SectionHeader
        icon={Server}
        title="System"
        description="Runtime environment, connectivity and application health."
        status="partial"
      />

      <SettingsPanel title="Runtime" description="Live status of this client session." icon={Server}>
        <div className="divide-y divide-[var(--border)]">
          <DetailRow label="Environment">
            <span className="rounded-md bg-[var(--background-secondary)] px-2 py-0.5 font-mono text-xs uppercase">
              {environment}
            </span>
          </DetailRow>
          <DetailRow label="API endpoint">
            <span className="font-mono text-xs">{apiHost}</span>
          </DetailRow>
          <DetailRow label="Connectivity">
            <span
              className="inline-flex items-center gap-1.5"
              style={{ color: online ? "var(--success)" : "var(--warning)" }}
            >
              {online ? <Wifi className="h-4 w-4" /> : <WifiOff className="h-4 w-4" />}
              {online ? "Online" : "Offline"}
            </span>
          </DetailRow>
          <DetailRow label="Offline engine">
            <span
              className="inline-flex items-center gap-1.5"
              style={{ color: swActive ? "var(--success)" : "var(--muted)" }}
            >
              <ShieldCheck className="h-4 w-4" />
              {swActive ? "Service worker active" : "Not registered"}
            </span>
          </DetailRow>
        </div>
      </SettingsPanel>

      <SettingsPanel title="Maintenance" description="Keep the app fresh on this device." icon={RefreshCw}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-[var(--muted)]">
            Reload the application to pick up the latest version and clear transient state.
          </p>
          <Button variant="secondary" onClick={() => window.location.reload()}>
            <RefreshCw className="h-4 w-4" />
            Reload app
          </Button>
        </div>
      </SettingsPanel>
    </div>
  );
}

export function AboutSection() {
  return (
    <div className="space-y-5">
      <SectionHeader
        icon={Info}
        title="About"
        description="Version and system information for MyHostel."
        status="partial"
      />
      <SettingsPanel title="Versions" icon={Info}>
        <div className="divide-y divide-[var(--border)]">
          <DetailRow label="Application">MyHostel SaaS</DetailRow>
          <DetailRow label="Frontend version">
            <span className="font-mono text-xs">v{APP_VERSION}</span>
          </DetailRow>
          <DetailRow label="Platform">Next.js · Django REST</DetailRow>
        </div>
      </SettingsPanel>
    </div>
  );
}

export function StorageSection() {
  return (
    <div className="space-y-5">
      <SectionHeader
        icon={HardDrive}
        title="Storage"
        description="On-device storage used for offline data, caches and downloads."
        status="ready"
      />
      {/* Reuse the existing PWA storage manager verbatim. */}
      <StorageCard />
    </div>
  );
}

/** A card that points at a full-page feature that lives elsewhere. */
function LinkOutPanel({
  icon: Icon,
  title,
  description,
  href,
  cta,
  points,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
  href: string;
  cta: string;
  points: string[];
}) {
  return (
    <SettingsPanel title={title} description={description} icon={Icon}>
      <ul className="mb-4 grid gap-2">
        {points.map((p) => (
          <li key={p} className="flex items-center gap-2 text-sm text-[var(--foreground-secondary)]">
            <span className="h-1.5 w-1.5 rounded-full bg-[var(--accent)]" aria-hidden />
            {p}
          </li>
        ))}
      </ul>
      <Link href={href}>
        <Button>
          {cta}
          <ArrowRight className="h-4 w-4" />
        </Button>
      </Link>
    </SettingsPanel>
  );
}

export function BackupsSection() {
  return (
    <div className="space-y-5">
      <SectionHeader
        icon={DatabaseBackup}
        title="Backups"
        description="Create, download, restore and schedule hostel data backups."
        status="ready"
      />
      <LinkOutPanel
        icon={DatabaseBackup}
        title="Backup & restore"
        description="Full backup management with retention and disaster-recovery modes."
        href="/backup"
        cta="Open backup manager"
        points={[
          "Create and download on-demand backups",
          "Restore from a previous snapshot",
          "Scheduled backups and retention policy",
        ]}
      />
    </div>
  );
}

export function DataManagementSection() {
  return (
    <div className="space-y-5">
      <SectionHeader
        icon={Archive}
        title="Data Management"
        description="Offline synchronization, exports and data lifecycle."
        status="ready"
      />
      <LinkOutPanel
        icon={Archive}
        title="Offline & sync"
        description="Review pending offline changes and sync status."
        href="/sync"
        cta="Open Sync Center"
        points={[
          "See queued offline changes",
          "Force a sync when back online",
          "Inspect sync conflicts and history",
        ]}
      />
    </div>
  );
}
