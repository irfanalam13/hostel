"use client";

import React from "react";
import { Spinner } from "./Spinner";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md";

type Props = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
  /** Shows a spinner and disables the button while a request is in flight. */
  loading?: boolean;
};

const VARIANTS: Record<Variant, string> = {
  primary: "bg-zinc-900 text-white hover:opacity-90",
  // `secondary` was already used in some pages without being defined — it
  // previously fell through to ghost styling. Now it's a first-class variant.
  secondary: "bg-zinc-100 text-zinc-900 hover:bg-zinc-200",
  ghost: "bg-white text-zinc-800 border border-zinc-200 hover:bg-zinc-50",
  danger: "bg-red-600 text-white hover:opacity-90",
};

const SIZES: Record<Size, string> = {
  sm: "px-2.5 py-1.5 text-xs",
  md: "px-3 py-2 text-sm",
};

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  disabled,
  className = "",
  children,
  ...props
}: Props) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-xl font-medium transition active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60 disabled:active:scale-100";

  return (
    <button
      {...props}
      // A loading button is always disabled so a double-click can't fire the
      // request twice.
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={`${base} ${VARIANTS[variant]} ${SIZES[size]} ${className}`}
    >
      {loading ? <Spinner size="sm" className="text-current" /> : null}
      {children}
    </button>
  );
}
