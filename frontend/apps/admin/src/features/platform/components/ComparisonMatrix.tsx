"use client";

import React, { useEffect, useMemo, useState } from "react";
import { Check, Minus } from "lucide-react";
import { EmptyState, Table, useToast } from "@hostel/ui";
import { platformApi } from "../api/platform.api";
import type { Comparison } from "../types/platform.types";

export function ComparisonMatrix() {
  const toast = useToast();
  const [data, setData] = useState<Comparison | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    platformApi.plans
      .comparison()
      .then(setData)
      .catch((e) => toast.error((e as Error).message))
      .finally(() => setLoading(false));
  }, [toast]);

  const featureGroups = useMemo(() => {
    if (!data) return [];
    const map = new Map<string, { name: string; rows: Comparison["features"] }>();
    for (const f of data.features) {
      if (!map.has(f.category_key)) map.set(f.category_key, { name: f.category_name, rows: [] });
      map.get(f.category_key)!.rows.push(f);
    }
    return [...map.values()];
  }, [data]);

  if (loading) return <div className="text-sm text-[var(--muted)]">Loading comparison…</div>;
  if (!data || data.plans.length === 0)
    return <EmptyState title="No plans to compare" description="Create a couple of plans first." />;

  const cols = data.plans;

  return (
    <Table>
      <thead>
        <tr className="border-b border-[var(--border)] text-left">
          <th className="sticky left-0 bg-[var(--card)] px-4 py-3 font-medium text-[var(--muted)]">
            Feature
          </th>
          {cols.map((p) => (
            <th key={p.id} className="px-4 py-3 text-center font-semibold text-[var(--foreground)]">
              {p.name}
              <div className="text-xs font-normal text-[var(--muted)]">
                {p.price_monthly} / {p.billing_interval}
              </div>
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {featureGroups.map((g) => (
          <React.Fragment key={g.name}>
            <tr className="bg-[var(--background-secondary)]">
              <td
                colSpan={cols.length + 1}
                className="px-4 py-1.5 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]"
              >
                {g.name}
              </td>
            </tr>
            {g.rows.map((f) => (
              <tr key={f.key} className="border-b border-[var(--border)]">
                <td className="sticky left-0 bg-[var(--card)] px-4 py-2.5 text-[var(--foreground-secondary)]">
                  {f.name}
                </td>
                {cols.map((p) => (
                  <td key={p.id} className="px-4 py-2.5 text-center">
                    {f.values[p.id] ? (
                      <Check className="mx-auto h-4 w-4 text-[var(--success)]" />
                    ) : (
                      <Minus className="mx-auto h-4 w-4 text-[var(--muted)]" />
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </React.Fragment>
        ))}

        <tr className="bg-[var(--background-secondary)]">
          <td
            colSpan={cols.length + 1}
            className="px-4 py-1.5 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]"
          >
            Limits
          </td>
        </tr>
        {data.limits.map((l) => (
          <tr key={l.key} className="border-b border-[var(--border)] last:border-0">
            <td className="sticky left-0 bg-[var(--card)] px-4 py-2.5 text-[var(--foreground-secondary)]">
              {l.name}
              {l.unit ? <span className="text-xs text-[var(--muted)]"> ({l.unit})</span> : null}
            </td>
            {cols.map((p) => (
              <td key={p.id} className="px-4 py-2.5 text-center text-[var(--foreground-secondary)]">
                {l.values[p.id] === null ? "∞" : l.values[p.id]}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </Table>
  );
}
