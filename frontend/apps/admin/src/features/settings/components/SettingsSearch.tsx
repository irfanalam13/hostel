"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Search, CornerDownLeft } from "lucide-react";
import { searchSections, sectionHref, STATUS_META } from "../registry";

/**
 * Searchable settings: type to filter every section by label, description or
 * keyword; arrow keys + Enter navigate. Complements the global Ctrl+K palette.
 */
export function SettingsSearch() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [index, setIndex] = useState(0);
  const wrapRef = useRef<HTMLDivElement>(null);

  const results = searchSections(query).slice(0, 8);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  function go(id: string) {
    router.push(sectionHref(id));
    setQuery("");
    setOpen(false);
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setOpen(true);
      setIndex((i) => (i + 1) % Math.max(1, results.length));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setIndex((i) => (i - 1 + results.length) % Math.max(1, results.length));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (results[index]) go(results[index].id);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div ref={wrapRef} className="relative">
      <div className="flex items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--card)] px-3 shadow-[var(--shadow-sm)] focus-within:border-[var(--accent)]">
        <Search className="h-4 w-4 shrink-0 text-[var(--muted)]" />
        <input
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIndex(0);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
          placeholder="Search settings…"
          aria-label="Search settings"
          className="w-full border-0 bg-transparent py-2.5 text-sm text-[var(--foreground)] outline-none placeholder:text-[var(--muted)] focus:ring-0"
        />
      </div>

      {open && results.length > 0 ? (
        <div className="absolute z-20 mt-2 w-full overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--card-elevated,var(--card))] p-1.5 shadow-[var(--shadow-lg)]">
          {results.map((s, i) => {
            const Icon = s.icon;
            const selected = i === index;
            return (
              <button
                key={s.id}
                type="button"
                onMouseEnter={() => setIndex(i)}
                onClick={() => go(s.id)}
                className={`flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left transition ${
                  selected ? "bg-[var(--accent)] text-white" : "text-[var(--foreground-secondary)] hover:bg-[var(--background-secondary)]"
                }`}
              >
                <Icon className={`h-4 w-4 shrink-0 ${selected ? "text-white" : "text-[var(--muted)]"}`} />
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-medium">{s.label}</span>
                  <span className={`block truncate text-xs ${selected ? "text-blue-100" : "text-[var(--muted)]"}`}>
                    {s.description}
                  </span>
                </span>
                {s.status !== "ready" ? (
                  <span
                    className={`shrink-0 rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase ${
                      selected ? "bg-white/20 text-white" : ""
                    }`}
                    style={selected ? undefined : { color: STATUS_META[s.status].tone, backgroundColor: `color-mix(in srgb, ${STATUS_META[s.status].tone} 14%, transparent)` }}
                  >
                    {STATUS_META[s.status].label}
                  </span>
                ) : (
                  selected && <CornerDownLeft className="h-3.5 w-3.5 shrink-0 text-white" />
                )}
              </button>
            );
          })}
        </div>
      ) : null}

      {open && query && results.length === 0 ? (
        <div className="absolute z-20 mt-2 w-full rounded-2xl border border-[var(--border)] bg-[var(--card)] px-4 py-6 text-center text-sm text-[var(--muted)] shadow-[var(--shadow-lg)]">
          No settings match &ldquo;{query}&rdquo;
        </div>
      ) : null}
    </div>
  );
}
