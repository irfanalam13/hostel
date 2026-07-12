"use client";

import { Card } from "@hostel/ui";
import type { AdmissionAnalytics } from "../types";

function StatCard({ label, value, accent }: { label: string; value: React.ReactNode; accent?: string }) {
  return (
    <Card className="!p-4">
      <div className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">{label}</div>
      <div className={`mt-1 text-2xl font-bold ${accent || "text-[var(--foreground)]"}`}>{value}</div>
    </Card>
  );
}

function Distribution({ title, data }: { title: string; data: Record<string, number> }) {
  const entries = Object.entries(data).filter(([k]) => k);
  const max = Math.max(1, ...entries.map(([, v]) => v));
  return (
    <Card>
      <div className="mb-3 text-sm font-semibold">{title}</div>
      {entries.length === 0 ? (
        <div className="text-sm text-[var(--muted)]">No data.</div>
      ) : (
        <div className="space-y-2">
          {entries.map(([key, value]) => (
            <div key={key}>
              <div className="mb-0.5 flex justify-between text-xs">
                <span className="capitalize text-[var(--foreground-secondary)]">{key.replace(/_/g, " ") || "—"}</span>
                <span className="font-medium">{value}</span>
              </div>
              <div className="h-1.5 w-full rounded-full bg-[var(--background-secondary)]">
                <div
                  className="h-1.5 rounded-full bg-[var(--accent)]"
                  style={{ width: `${(value / max) * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

export function AdmissionAnalytics({ data }: { data: AdmissionAnalytics }) {
  const c = data.cards;
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-7">
        <StatCard label="Today" value={c.today} />
        <StatCard label="Pending" value={c.pending} accent="text-amber-600" />
        <StatCard label="Approved" value={c.approved} accent="text-emerald-600" />
        <StatCard label="Rejected" value={c.rejected} accent="text-red-600" />
        <StatCard label="This month" value={c.monthly} />
        <StatCard label="Occupancy" value={`${c.occupancy}%`} />
        <StatCard label="Revenue" value={`Rs ${c.revenue.toLocaleString()}`} accent="text-[var(--accent)]" />
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Distribution title="By status" data={data.charts.status} />
        <Distribution title="By education level" data={data.charts.education} />
        <Distribution title="By food preference" data={data.charts.food} />
        <Distribution title="By district" data={data.charts.district} />
      </div>
    </div>
  );
}
