"use client";

import React from "react";

/** Base shimmer block. Compose these for any loading placeholder. */
export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-[color-mix(in_srgb,var(--muted)_22%,transparent)] ${className}`} />;
}

/** A grid of stat cards — matches the dashboard / billing summary layout. */
export function StatCardsSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-4">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="rounded-[20px] border border-[var(--border)] bg-[var(--card)] p-4">
          <Skeleton className="mb-3 h-3 w-20" />
          <Skeleton className="h-7 w-24" />
        </div>
      ))}
    </div>
  );
}

/** Table placeholder with a header row and N body rows. */
export function TableSkeleton({ rows = 6, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="overflow-hidden rounded-[20px] border border-[var(--border)] bg-[var(--card)] shadow-[var(--shadow-sm)]">
      <div className="flex gap-4 border-b border-[var(--border)] bg-[var(--background-secondary)] px-4 py-3">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} className="h-3 flex-1" />
        ))}
      </div>
      <div className="divide-y divide-[var(--border)]">
        {Array.from({ length: rows }).map((_, r) => (
          <div key={r} className="flex gap-4 px-4 py-3.5">
            {Array.from({ length: cols }).map((_, c) => (
              <Skeleton key={c} className="h-4 flex-1" />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

/** Full-page skeleton: a header band, stat cards and a table. */
export function PageSkeleton() {
  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-3 w-64" />
      </div>
      <StatCardsSkeleton />
      <TableSkeleton />
    </div>
  );
}
