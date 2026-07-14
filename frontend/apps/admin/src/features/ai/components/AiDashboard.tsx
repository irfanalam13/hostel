"use client";

import React from "react";
import { useApi } from "@hostel/hooks";
import { Spinner } from "@hostel/ui";

import { aiApi } from "../api/ai.api";
import { StatCard } from "./primitives";

export function AiDashboard() {
  const { data, loading, error } = useApi(() => aiApi.dashboard(), { immediate: true, deps: [] });

  if (loading && !data) {
    return (
      <div className="flex justify-center py-16">
        <Spinner />
      </div>
    );
  }
  if (error || !data) {
    return (
      <div className="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-6 text-sm text-[var(--muted)]">
        Could not load AI usage right now.
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        <StatCard label="Requests today" value={data.requests_today} />
        <StatCard label="Tokens today" value={data.tokens_today.toLocaleString()} />
        <StatCard label="Avg response" value={`${data.avg_latency_ms} ms`} />
        <StatCard label="Est. cost (today)" value={`$${data.estimated_cost_usd}`} hint="self-hosted = $0" />
        <StatCard label="Active conversations" value={data.active_conversations} />
        <StatCard label="Total requests" value={data.total_requests} />
      </div>

      <div className="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-4 shadow-[var(--shadow-sm)]">
        <div className="text-sm font-semibold text-[var(--foreground)]">Model usage</div>
        {data.model_usage.length === 0 ? (
          <p className="mt-2 text-sm text-[var(--muted)]">No AI activity yet.</p>
        ) : (
          <ul className="mt-3 space-y-2">
            {data.model_usage.map((m) => (
              <li key={m.model} className="flex items-center justify-between text-sm">
                <span className="font-medium text-[var(--foreground)]">{m.model}</span>
                <span className="text-[var(--muted)]">{m.requests} requests</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
