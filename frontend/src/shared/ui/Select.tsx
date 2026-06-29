"use client";

import React from "react";

type Option = { value: string; label: string };

type Props = React.SelectHTMLAttributes<HTMLSelectElement> & {
  label?: string;
  options?: Option[];
  placeholder?: string;
};

export function Select({ label, options, placeholder, className = "", children, ...props }: Props) {
  return (
    <label className="block">
      {label ? <div className="text-sm mb-1 text-[var(--foreground-secondary)]">{label}</div> : null}
      <select
        {...props}
        className={`w-full rounded-xl border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-[var(--foreground)] outline-none focus:border-[var(--accent)] focus:ring-4 focus:ring-[color-mix(in_srgb,var(--accent)_18%,transparent)] ${className}`}
      >
        {placeholder !== undefined ? <option value="">{placeholder}</option> : null}
        {options
          ? options.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))
          : children}
      </select>
    </label>
  );
}
