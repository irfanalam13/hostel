"use client";

import { useCallback, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import {
  AlertTriangle,
  Bell,
  Download,
  Gauge,
  RefreshCcw,
  RefreshCw,
  WifiOff,
} from "lucide-react";
import { getAnalyticsReport } from "./api";
import type { AnalyticsReport } from "./types";

// recharts is heavy; keep it out of the initial dashboard bundle. The chart
// self-hides on 403, so this is a no-op for non-super-admins.
const TrendsChart = dynamic(() => import("./TrendsChart").then((m) => m.TrendsChart), {
  ssr: false,
});

const WINDOWS = [7, 30, 90];
const pct = (rate: number) => `${Math.round((rate || 0) * 100)}%`;

function RateTile({
  label,
  value,
  hint,
  icon: Icon,
  tone = "accent",
}: {
  label: string;
  value: string;
  hint?: string;
  icon: React.ComponentType<{ className?: string }>;
  tone?: "accent" | "success" | "warning" | "error" | "muted";
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
        <span className="rounded-lg p-1.5" style={{ color, backgroundColor: `color-mix(in srgb, ${color} 12%, transparent)` }}>
          <Icon className="h-4 w-4" />
        </span>
      </div>
      <div className="mt-2 text-xl font-bold text-[var(--foreground)] tabular-nums">{value}</div>
      {hint && <p className="mt-0.5 text-[11px] text-[var(--muted)]">{hint}</p>}
    </div>
  );
}

function Breakdown({ title, data }: { title: string; data: Record<string, number> }) {
  const entries = Object.entries(data).filter(([, n]) => n > 0).sort((a, b) => b[1] - a[1]);
  const total = entries.reduce((s, [, n]) => s + n, 0);
  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-4">
      <h4 className="mb-3 text-xs font-semibold text-[var(--muted)]">{title}</h4>
      {entries.length === 0 ? (
        <p className="text-xs text-[var(--muted)]">No data yet.</p>
      ) : (
        <ul className="space-y-2">
          {entries.map(([name, n]) => (
            <li key={name} className="text-xs">
              <div className="mb-0.5 flex justify-between text-[var(--foreground-secondary)]">
                <span className="capitalize">{name.toLowerCase()}</span>
                <span className="tabular-nums">{Math.round((n / total) * 100)}%</span>
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-[var(--background-secondary)]">
                <div className="h-full rounded-full bg-[var(--accent)]" style={{ width: `${(n / total) * 100}%` }} />
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/**
 * PWA analytics report (owner/manager only). Hides itself for non-staff users
 * (the report endpoint returns 403). Shows the ten tracked PWA metrics over a
 * selectable window.
 */
export function AnalyticsPanel() {
  const [days, setDays] = useState(30);
  const [report, setReport] = useState<AnalyticsReport | null>(null);
  const [forbidden, setForbidden] = useState(false);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async (d: number) => {
    setLoading(true);
    try {
      setReport(await getAnalyticsReport(d));
      setForbidden(false);
    } catch (err) {
      if ((err as { status?: number })?.status === 403) setForbidden(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh(days);
  }, [days, refresh]);

  if (forbidden) return null;

  const offlineMins = report ? Math.round(report.offline_usage.total_seconds / 60) : 0;

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-[11px] font-bold uppercase tracking-wider text-[var(--foreground-secondary)]">
          PWA analytics
        </h3>
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg bg-[var(--background-secondary)] p-0.5 text-xs">
            {WINDOWS.map((d) => (
              <button
                key={d}
                onClick={() => setDays(d)}
                className={`rounded-md px-2 py-1 font-medium transition ${
                  days === d ? "bg-[var(--accent)] text-white" : "text-[var(--foreground-secondary)]"
                }`}
              >
                {d}d
              </button>
            ))}
          </div>
          <button
            onClick={() => refresh(days)}
            disabled={loading}
            className="inline-flex items-center gap-1 text-xs font-medium text-[var(--accent)] hover:underline disabled:opacity-50"
          >
            <RefreshCw className={`h-3 w-3 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <RateTile
          label="Install rate"
          value={report ? pct(report.install.rate) : "…"}
          hint={report ? `${report.install.installed}/${report.install.prompts} prompts` : undefined}
          icon={Download}
          tone="success"
        />
        <RateTile
          label="Update rate"
          value={report ? pct(report.update.rate) : "…"}
          hint={report ? `${report.update.applied}/${report.update.available}` : undefined}
          icon={RefreshCcw}
        />
        <RateTile
          label="Push open rate"
          value={report ? pct(report.push.open_rate) : "…"}
          hint={report ? `${report.push.opened}/${report.push.received} opened` : undefined}
          icon={Bell}
        />
        <RateTile
          label="Cache efficiency"
          value={report ? pct(report.cache.efficiency) : "…"}
          hint={report ? `${report.cache.hits} hits / ${report.cache.misses} miss` : undefined}
          icon={Gauge}
          tone="success"
        />
        <RateTile
          label="Sync success"
          value={report ? pct(report.sync.success_rate) : "…"}
          hint={report ? `${report.sync.success} ok / ${report.sync.failure} fail` : undefined}
          icon={RefreshCw}
          tone={report && report.sync.failure > 0 ? "warning" : "success"}
        />
        <RateTile
          label="Errors"
          value={report ? String(report.errors.total) : "…"}
          hint="client errors"
          icon={AlertTriangle}
          tone={report && report.errors.total > 0 ? "error" : "success"}
        />
        <RateTile
          label="Offline usage"
          value={report ? `${offlineMins}m` : "…"}
          hint={report ? `${report.offline_usage.users} user(s)` : undefined}
          icon={WifiOff}
          tone="muted"
        />
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <Breakdown title="Device types" data={report?.device_types ?? {}} />
        <Breakdown title="Browser support" data={report?.browsers ?? {}} />
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-4">
          <h4 className="mb-3 text-xs font-semibold text-[var(--muted)]">Feature adoption</h4>
          {report && report.feature_adoption.length > 0 ? (
            <ul className="space-y-1.5 text-xs">
              {report.feature_adoption.slice(0, 8).map((f) => (
                <li key={f.name} className="flex justify-between text-[var(--foreground-secondary)]">
                  <span className="capitalize">{f.name || "—"}</span>
                  <span className="tabular-nums text-[var(--muted)]">
                    {f.uses} uses · {f.users} users
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-[var(--muted)]">No data yet.</p>
          )}
        </div>
      </div>

      <TrendsChart />
    </section>
  );
}
