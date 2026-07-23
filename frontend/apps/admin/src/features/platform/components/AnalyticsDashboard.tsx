"use client";

import React, { useEffect, useState } from "react";
import { Table, useToast } from "@hostel/ui";
import { platformApi } from "../api/platform.api";
import type { Analytics } from "../types/platform.types";

function Tile({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-[20px] border border-[var(--border)] bg-[var(--card)] p-5">
      <div className="text-sm text-[var(--muted)]">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-[var(--foreground)]">{value}</div>
      {sub ? <div className="text-xs text-[var(--muted)]">{sub}</div> : null}
    </div>
  );
}

export function AnalyticsDashboard() {
  const toast = useToast();
  const [data, setData] = useState<Analytics | null>(null);

  useEffect(() => {
    platformApi
      .analytics()
      .then(setData)
      .catch((e) => toast.error((e as Error).message));
  }, [toast]);

  if (!data) return <div className="text-sm text-[var(--muted)]">Loading analytics…</div>;

  const cur = data.currency;
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Tile label="MRR" value={`${cur} ${data.mrr}`} sub="monthly recurring" />
        <Tile label="ARR" value={`${cur} ${data.arr}`} sub="annual run-rate" />
        <Tile label="Active hostels" value={String(data.hostels.active)} sub={`${data.hostels.trial} trial · ${data.hostels.no_plan} no plan`} />
        <Tile label="Active plans" value={String(data.plans.active)} sub={`${data.plans.public} public of ${data.plans.total}`} />
      </div>

      <div>
        <div className="mb-2 text-sm font-semibold text-[var(--foreground)]">Revenue by plan</div>
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Plan</th>
              <th className="px-4 py-3 font-medium text-right">Hostels</th>
              <th className="px-4 py-3 font-medium text-right">MRR</th>
            </tr>
          </thead>
          <tbody>
            {data.plan_distribution.map((row) => (
              <tr key={row.plan} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-2.5 text-[var(--foreground)]">{row.name}</td>
                <td className="px-4 py-2.5 text-right text-[var(--foreground-secondary)]">{row.hostels}</td>
                <td className="px-4 py-2.5 text-right text-[var(--foreground-secondary)]">{cur} {row.mrr}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div>
          <div className="mb-2 text-sm font-semibold text-[var(--foreground)]">Top feature adoption</div>
          <div className="space-y-2">
            {data.most_used_features.map((f) => (
              <div key={f.key} className="rounded-xl border border-[var(--border)] bg-[var(--card)] px-4 py-2.5">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-[var(--foreground)]">{f.name}</span>
                  <span className="text-[var(--muted)]">{f.plans_enabled} plans · {f.plan_percent}%</span>
                </div>
                <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-[var(--background-secondary)]">
                  <div className="h-full rounded-full bg-[var(--accent)]" style={{ width: `${f.plan_percent}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="mb-2 text-sm font-semibold text-[var(--foreground)]">
            Unused features ({data.unused_features.length})
          </div>
          {data.unused_features.length === 0 ? (
            <div className="text-sm text-[var(--muted)]">Every feature is enabled in at least one plan.</div>
          ) : (
            <div className="flex flex-wrap gap-1.5">
              {data.unused_features.map((f) => (
                <span key={f.key} className="rounded-full bg-[var(--background-secondary)] px-2.5 py-1 text-xs text-[var(--foreground-secondary)]">
                  {f.name}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
