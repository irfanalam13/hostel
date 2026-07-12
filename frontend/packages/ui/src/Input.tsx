"use client";

import React from "react";

type Props = React.InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
};

export function Input({ label, className = "", ...props }: Props) {
  return (
    <label className="block">
      {label ? <div className="text-sm mb-1 text-[var(--foreground-secondary)]">{label}</div> : null}
      <input
        {...props}
        className={`w-full rounded-xl border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-[var(--foreground)] outline-none placeholder:text-[var(--muted)] focus:border-[var(--accent)] focus:ring-4 focus:ring-[color-mix(in_srgb,var(--accent)_18%,transparent)] ${className}`}
      />
    </label>
  );
}
