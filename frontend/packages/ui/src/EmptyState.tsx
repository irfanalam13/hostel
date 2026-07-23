"use client";

import React from "react";

/**
 * Friendly placeholder shown when a list/table has no rows (no residents, no
 * payments, no rooms…). Optionally renders a call-to-action.
 */
export function EmptyState({
  title,
  description,
  icon = "📭",
  action,
  className = "",
}: {
  title: string;
  description?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`grid place-items-center gap-2 rounded-2xl border border-dashed border-zinc-300 bg-white px-6 py-12 text-center ${className}`}
    >
      <div className="text-3xl" aria-hidden>
        {icon}
      </div>
      <div className="text-sm font-semibold text-zinc-800">{title}</div>
      {description ? <div className="max-w-sm text-sm text-zinc-500">{description}</div> : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}
