"use client";

import React from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getAnalyticsTrends } from "./api";
import type { AnalyticsTrends, TrendGranularity } from "./types";

const GRANULARITIES: { key: TrendGranularity; label: string }[] = [
  { key: "day", label: "Daily" },
  { key: "week", label: "Weekly" },
  { key: "month", label: "Monthly" },
];

// Distinct, colour-blind-friendly palette for up to 6 series.
const PALETTE = ["#6366f1", "#10b981", "#f59e0b", "#ef4444", "#06b6d4", "#a855f7"];

/** Top-N event types by total volume, so the chart stays readable. */
function topSeries(trends: AnalyticsTrends, n = 6): string[] {
  return Object.entries(trends.totals)
    .sort((a, b) => b[1] - a[1])
    .slice(0, n)
    .map(([eventType]) => eventType);
}

function toChartRows(trends: AnalyticsTrends, series: string[]) {
  return trends.buckets.map((bucket) => {
    const row: Record<string, string | number> = { bucket };
    for (const s of series) row[s] = trends.series[bucket]?.[s] ?? 0;
    return row;
  });
}

/**
 * Historical event trends, served from the durable rollup aggregation tier
 * (Phase 8) — not the transactional table. Super-admin only; hides itself on
 * 403 so it can sit inside the shared PWA analytics panel.
 */
export function TrendsChart() {
  const [granularity, setGranularity] = React.useState<TrendGranularity>("day");
  const [trends, setTrends] = React.useState<AnalyticsTrends | null>(null);
  const [forbidden, setForbidden] = React.useState(false);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    let alive = true;
    setLoading(true);
    getAnalyticsTrends(granularity === "month" ? 365 : 90, granularity)
      .then((t) => alive && setTrends(t))
      .catch((err) => {
        if ((err as { status?: number })?.status === 403) setForbidden(true);
      })
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [granularity]);

  if (forbidden) return null;

  const series = trends ? topSeries(trends) : [];
  const rows = trends ? toChartRows(trends, series) : [];
  const hasData = rows.length > 0 && series.length > 0;

  return (
    <section className="space-y-3 rounded-2xl border border-[var(--border)] bg-[var(--card)] p-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-[11px] font-bold uppercase tracking-wider text-[var(--foreground-secondary)]">
            Event trends
          </h3>
          <p className="text-[11px] text-[var(--muted)]">
            From the durable rollup pipeline · survives raw-event retention.
          </p>
        </div>
        <div className="flex rounded-lg bg-[var(--background-secondary)] p-0.5 text-xs">
          {GRANULARITIES.map((g) => (
            <button
              key={g.key}
              onClick={() => setGranularity(g.key)}
              className={`rounded-md px-2 py-1 font-medium transition ${
                granularity === g.key
                  ? "bg-[var(--accent)] text-white"
                  : "text-[var(--foreground-secondary)]"
              }`}
            >
              {g.label}
            </button>
          ))}
        </div>
      </div>

      {loading && !trends ? (
        <div className="flex h-64 items-center justify-center text-xs text-[var(--muted)]">Loading…</div>
      ) : !hasData ? (
        <div className="flex h-64 items-center justify-center text-xs text-[var(--muted)]">
          No trend data yet.
        </div>
      ) : (
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={rows} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis dataKey="bucket" tick={{ fontSize: 11, fill: "var(--foreground-secondary)" }} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: "var(--foreground-secondary)" }} tickLine={false} allowDecimals={false} width={40} />
              <Tooltip
                contentStyle={{
                  background: "var(--card-elevated)",
                  border: "1px solid var(--border)",
                  borderRadius: 12,
                  fontSize: 12,
                }}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              {series.map((s, i) => (
                <Line
                  key={s}
                  type="monotone"
                  dataKey={s}
                  stroke={PALETTE[i % PALETTE.length]}
                  strokeWidth={2}
                  dot={false}
                  name={s.replace(/_/g, " ").toLowerCase()}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}
