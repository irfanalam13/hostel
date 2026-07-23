"use client";

import { Sparkles } from "lucide-react";

/** Small pill marking a surface that's designed but not yet wired to real data. */
export function ComingSoonBadge({ className = "" }: { className?: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border border-[var(--border)] bg-[var(--background-secondary)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)] ${className}`}
    >
      <Sparkles className="h-3 w-3" />
      Coming soon
    </span>
  );
}
