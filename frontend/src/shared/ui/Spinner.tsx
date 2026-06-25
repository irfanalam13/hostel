"use client";

import React from "react";

type Size = "sm" | "md" | "lg";

const SIZES: Record<Size, string> = {
  sm: "h-4 w-4 border-2",
  md: "h-6 w-6 border-2",
  lg: "h-8 w-8 border-[3px]",
};

export function Spinner({
  size = "md",
  className = "",
  label = "Loading",
}: {
  size?: Size;
  className?: string;
  label?: string;
}) {
  return (
    <span
      role="status"
      aria-label={label}
      className={`inline-block animate-spin rounded-full border-current border-t-transparent text-zinc-400 ${SIZES[size]} ${className}`}
    />
  );
}

/** Centered spinner for in-card / in-section data fetches. */
export function LoadingSpinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="grid place-items-center gap-3 py-10 text-zinc-500">
      <Spinner size="lg" />
      <div className="text-sm">{label}</div>
    </div>
  );
}
