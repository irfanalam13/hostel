import React from "react";
import { Building2 } from "lucide-react";
import { BRAND } from "../content";

type Props = {
  className?: string;
  /** Hide the wordmark, show only the icon (e.g. tight mobile headers). */
  iconOnly?: boolean;
};

export function Logo({ className = "", iconOnly = false }: Props) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <span
        aria-hidden
        className="grid h-9 w-9 place-items-center rounded-xl bg-[var(--accent)] text-white shadow-[var(--shadow-sm)]"
      >
        <Building2 className="h-5 w-5" />
      </span>
      {!iconOnly && (
        <span className="text-lg font-bold tracking-tight text-[var(--foreground)]">
          {BRAND.name}
        </span>
      )}
    </span>
  );
}
