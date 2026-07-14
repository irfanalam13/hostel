"use client";

import React from "react";

import type { LookupResult } from "../types/opsgov.types";

type Props = {
  label: string;
  placeholder?: string;
  /** Currently selected option (controlled). */
  value: LookupResult | null;
  onChange: (value: LookupResult | null) => void;
  /** Debounced search callback returning matches. */
  fetcher: (q: string) => Promise<LookupResult[]>;
  disabled?: boolean;
};

/**
 * Debounced searchable combobox (typeahead). Backs the override builder's
 * tenant/user selectors — fetches matches from a server lookup as the operator
 * types, so it scales past what a plain <select> could hold.
 */
export function TargetCombobox({ label, placeholder, value, onChange, fetcher, disabled }: Props) {
  const [query, setQuery] = React.useState("");
  const [results, setResults] = React.useState<LookupResult[]>([]);
  const [open, setOpen] = React.useState(false);
  const [loading, setLoading] = React.useState(false);
  const [active, setActive] = React.useState(0);
  const boxRef = React.useRef<HTMLDivElement>(null);
  const listboxId = React.useId();

  // Debounced fetch on query change (only while open, no selection pinned).
  React.useEffect(() => {
    if (!open) return;
    let alive = true;
    setLoading(true);
    const t = setTimeout(() => {
      fetcher(query)
        .then((r) => alive && setResults(r))
        .catch(() => alive && setResults([]))
        .finally(() => alive && setLoading(false));
    }, 250);
    return () => {
      alive = false;
      clearTimeout(t);
    };
  }, [query, open, fetcher]);

  // Close on outside click.
  React.useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const select = (r: LookupResult) => {
    onChange(r);
    setOpen(false);
    setQuery("");
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (!open) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => Math.min(a + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (e.key === "Enter" && results[active]) {
      e.preventDefault();
      select(results[active]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  return (
    <div ref={boxRef} className="relative">
      <div className="mb-1 text-sm text-[var(--foreground-secondary)]">{label}</div>

      {value ? (
        <div className="flex items-center justify-between gap-2 rounded-xl border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-sm">
          <span className="truncate">
            {value.label}
            {value.email ? <span className="text-[var(--muted)]"> · {value.email}</span> : null}
          </span>
          {!disabled && (
            <button
              type="button"
              onClick={() => onChange(null)}
              aria-label="Clear selection"
              className="shrink-0 text-[var(--foreground-secondary)] hover:text-[var(--foreground)]"
            >
              ✕
            </button>
          )}
        </div>
      ) : (
        <input
          value={query}
          disabled={disabled}
          onChange={(e) => {
            setQuery(e.target.value);
            setActive(0);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
          placeholder={placeholder}
          className="w-full rounded-xl border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-sm outline-none focus:border-[var(--accent)]"
          role="combobox"
          aria-expanded={open}
          aria-controls={listboxId}
          aria-autocomplete="list"
        />
      )}

      {open && !value && (
        <div className="absolute z-20 mt-1 max-h-56 w-full overflow-auto rounded-xl border border-[var(--border)] bg-[var(--card-elevated)] shadow-[var(--shadow-lg)]">
          {loading ? (
            <div className="px-3 py-2 text-xs text-[var(--muted)]">Searching…</div>
          ) : results.length === 0 ? (
            <div className="px-3 py-2 text-xs text-[var(--muted)]">
              {query ? "No matches." : "Type to search…"}
            </div>
          ) : (
            <ul id={listboxId} role="listbox">
              {results.map((r, i) => (
                <li
                  key={String(r.id)}
                  role="option"
                  aria-selected={i === active}
                  onMouseEnter={() => setActive(i)}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    select(r);
                  }}
                  className={`cursor-pointer px-3 py-2 text-sm ${
                    i === active ? "bg-[var(--background-secondary)]" : ""
                  }`}
                >
                  <div className="truncate">{r.label}</div>
                  {(r.email || r.role) && (
                    <div className="truncate text-xs text-[var(--muted)]">
                      {r.email}
                      {r.email && r.role ? " · " : ""}
                      {r.role}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
