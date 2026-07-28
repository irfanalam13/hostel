"use client";

import React from "react";

type Size = "sm" | "md" | "lg";

const SIZES: Record<Size, string> = {
  sm: "text-sm",
  md: "text-lg",
  lg: "text-2xl",
};

type Props = {
  /** Current rating, 0..max. Supports partial (half/fractional) fill in display mode. */
  value: number;
  max?: number;
  size?: Size;
  /** CSS color for filled stars — defaults to the admin app's accent token, but
   * accepts a raw override (e.g. `var(--site-accent)`) so hostel-site can theme it. */
  color?: string;
  /** Presence of onChange switches this into an interactive, clickable rating input. */
  onChange?: (value: number) => void;
  className?: string;
  "aria-label"?: string;
};

function Star({ fill, size, color }: { fill: number; size: Size; color: string }) {
  const clippedFill = Math.max(0, Math.min(1, fill));
  return (
    <span className={`relative inline-block ${SIZES[size]}`} style={{ lineHeight: 1 }}>
      <span aria-hidden="true" className="text-[var(--border)]">
        ★
      </span>
      <span
        aria-hidden="true"
        className="absolute inset-0 overflow-hidden"
        style={{ width: `${clippedFill * 100}%`, color }}
      >
        ★
      </span>
    </span>
  );
}

export function StarRating({
  value,
  max = 5,
  size = "md",
  color = "var(--accent)",
  onChange,
  className = "",
  "aria-label": ariaLabel,
}: Props) {
  const interactive = typeof onChange === "function";
  const stars = Array.from({ length: max }, (_, i) => i + 1);

  if (!interactive) {
    return (
      <span
        className={`inline-flex items-center gap-0.5 ${className}`}
        role="img"
        aria-label={ariaLabel ?? `Rated ${value.toFixed(1)} out of ${max}`}
      >
        {stars.map((n) => (
          <Star key={n} size={size} color={color} fill={Math.max(0, Math.min(1, value - (n - 1)))} />
        ))}
      </span>
    );
  }

  return (
    <span className={`inline-flex items-center gap-0.5 ${className}`} role="radiogroup" aria-label={ariaLabel ?? "Rating"}>
      {stars.map((n) => (
        <button
          key={n}
          type="button"
          role="radio"
          aria-checked={value === n}
          aria-label={`${n} star${n === 1 ? "" : "s"}`}
          onClick={() => onChange!(n)}
          className="rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color-mix(in_srgb,var(--accent)_30%,transparent)]"
        >
          <Star size={size} color={color} fill={n <= value ? 1 : 0} />
        </button>
      ))}
    </span>
  );
}
