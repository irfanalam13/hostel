"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  Bell,
  CheckCircle2,
  Cloud,
  CloudOff,
  Cpu,
  Download,
  HardDrive,
  RefreshCw,
  Users,
  Wifi,
  XCircle,
} from "lucide-react";
import { usePwa } from "@hostel/pwa";
import { getServiceWorkerVersion } from "@hostel/pwa";
import { permissionState } from "@hostel/pwa";
import { getSystemStatus } from "./api";
import { APP_VERSION, type SystemStatus } from "./types";

const POLL_MS = 30_000;

type Tone = "accent" | "success" | "warning" | "error" | "muted";

function Tile({
  label,
  value,
  hint,
  icon: Icon,
  tone = "accent",
}: {
  label: string;
  value: string | number;
  hint?: string;
  icon: React.ComponentType<{ className?: string }>;
  tone?: Tone;
}) {
  const color =
    tone === "success"
      ? "var(--success)"
      : tone === "warning"
        ? "var(--warning)"
        : tone === "error"
          ? "var(--error)"
          : tone === "muted"
            ? "var(--muted)"
            : "var(--accent)";
  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-4">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-[var(--muted)]">{label}</span>
        <span
          className="rounded-lg p-1.5"
          style={{ color, backgroundColor: `color-mix(in srgb, ${color} 12%, transparent)` }}
        >
          <Icon className="h-4 w-4" />
        </span>
      </div>
      <div className="mt-2 text-xl font-bold text-[var(--foreground)] tabular-nums">{value}</div>
      {hint && <p className="mt-0.5 text-[11px] text-[var(--muted)]">{hint}</p>}
    </div>
  );
}

/**
 * System & PWA status. Combines tenant-wide server aggregates (owner/manager
 * only) with always-available device-local metrics read straight from the
 * browser / service worker.
 */
export function SystemStatusPanel() {
  const { isOnline, isInstalled, pendingSync } = usePwa();
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [forbidden, setForbidden] = useState(false);
  const [loading, setLoading] = useState(true);
  const [swVersion, setSwVersion] = useState<string | null>(null);
  const [notif, setNotif] = useState<string>("default");

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setStatus(await getSystemStatus());
      setForbidden(false);
    } catch (err) {
      // Non-staff users get 403 — still show device metrics.
      if ((err as { status?: number })?.status === 403) setForbidden(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const id = window.setInterval(refresh, POLL_MS);
    return () => window.clearInterval(id);
  }, [refresh]);

  useEffect(() => {
    void getServiceWorkerVersion().then(setSwVersion);
    setNotif(permissionState());
  }, []);

  const health = status?.api_health;
  const healthTone: Tone = !health ? "muted" : health.status === "ok" ? "success" : "error";
  const notifTone: Tone =
    notif === "granted" ? "success" : notif === "denied" ? "error" : "muted";

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-[11px] font-bold uppercase tracking-wider text-[var(--foreground-secondary)]">
          System &amp; PWA status
        </h3>
        <button
          onClick={refresh}
          disabled={loading}
          className="inline-flex items-center gap-1 text-xs font-medium text-[var(--accent)] hover:underline disabled:opacity-50"
        >
          <RefreshCw className={`h-3 w-3 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
        {/* --- Server / tenant metrics --- */}
        <Tile
          label="Online users"
          value={status ? status.users.online : forbidden ? "—" : "…"}
          hint={status ? `${status.users.members} members` : forbidden ? "Admin only" : undefined}
          icon={Users}
          tone="success"
        />
        <Tile
          label="Offline users"
          value={status ? status.users.offline : "—"}
          icon={CloudOff}
          tone="muted"
        />
        <Tile
          label="Installed PWAs"
          value={status ? status.users.installed_active : "—"}
          hint="active installs"
          icon={Download}
        />
        <Tile
          label="Push subscribers"
          value={status ? status.pwa.push_subscribers : "—"}
          icon={Bell}
        />
        <Tile
          label="Pending sync jobs"
          value={status ? status.sync.pending : pendingSync}
          hint={status ? `${pendingSync} on this device` : "this device"}
          icon={RefreshCw}
          tone={(status?.sync.pending || pendingSync) > 0 ? "warning" : "success"}
        />
        <Tile
          label="Failed syncs"
          value={status ? status.sync.failed : "—"}
          icon={XCircle}
          tone={status && status.sync.failed > 0 ? "error" : "success"}
        />
        <Tile
          label="Background tasks"
          value={status ? status.background_tasks.total : "—"}
          hint={status ? `${status.background_tasks.scheduled_notifications} scheduled` : undefined}
          icon={Cpu}
        />
        <Tile
          label="API health"
          value={health ? (health.status === "ok" ? "Healthy" : "Degraded") : "—"}
          hint={
            health
              ? `db ${health.database ? "✓" : "✕"} · cache ${health.cache ? "✓" : "✕"} · celery ${health.celery ? "✓" : "✕"}`
              : undefined
          }
          icon={Activity}
          tone={healthTone}
        />
        <Tile
          label="Application version"
          value={status?.pwa.app_version ?? APP_VERSION}
          icon={CheckCircle2}
          tone="muted"
        />

        {/* --- Device-local metrics --- */}
        <Tile
          label="Connection"
          value={isOnline ? "Online" : "Offline"}
          hint="this device"
          icon={isOnline ? Wifi : CloudOff}
          tone={isOnline ? "success" : "error"}
        />
        <Tile
          label="Notifications"
          value={notif === "granted" ? "On" : notif === "denied" ? "Blocked" : "Off"}
          hint={status && !status.pwa.notifications_configured ? "server not configured" : "this device"}
          icon={Bell}
          tone={notifTone}
        />
        <Tile
          label="Service Worker"
          value={swVersion ?? "inactive"}
          hint={isInstalled ? "installed app" : "browser tab"}
          icon={Cloud}
          tone={swVersion ? "accent" : "muted"}
        />
        <Tile
          label="Cache version"
          value={swVersion ?? "—"}
          icon={HardDrive}
          tone="muted"
        />
      </div>
    </section>
  );
}
