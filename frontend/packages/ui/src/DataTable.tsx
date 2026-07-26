"use client";
import React from "react";

export type Column<T> = {
  /** Stable key; also used to read `row[key]` when no `accessor` is given. */
  key: string;
  header: string;
  /** Value used for sorting/searching (defaults to `row[key]`). */
  accessor?: (row: T) => unknown;
  /** Custom cell renderer (defaults to the string form of the value). */
  render?: (row: T) => React.ReactNode;
  sortable?: boolean;
  className?: string;
  align?: "left" | "right" | "center";
};

type SortState = { key: string; dir: "asc" | "desc" };

export type DataTableProps<T> = {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  loading?: boolean;
  emptyMessage?: string;
  /** Show the built-in client-side search box. */
  searchable?: boolean;
  searchPlaceholder?: string;
  /** Extra filter controls rendered in the toolbar (left of search). */
  toolbar?: React.ReactNode;
  /** Client-side page size. Omit / 0 to disable pagination. */
  pageSize?: number;
  initialSort?: SortState;
  onRowClick?: (row: T) => void;
};

function valueOf<T>(row: T, col: Column<T>): unknown {
  return col.accessor ? col.accessor(row) : (row as Record<string, unknown>)[col.key];
}

function compare(a: unknown, b: unknown): number {
  if (a == null && b == null) return 0;
  if (a == null) return -1;
  if (b == null) return 1;
  if (typeof a === "number" && typeof b === "number") return a - b;
  return String(a).localeCompare(String(b), undefined, { numeric: true });
}

/**
 * Reusable data table: client-side search, column sort and pagination, theme
 * aware, keyboard/ARIA friendly. Pass `render` for rich cells; sorting/search
 * always use the raw `accessor` value so they stay correct regardless of markup.
 */
export function DataTable<T>({
  columns,
  rows,
  rowKey,
  loading = false,
  emptyMessage = "No records found.",
  searchable = false,
  searchPlaceholder = "Search…",
  toolbar,
  pageSize = 0,
  initialSort,
  onRowClick,
}: DataTableProps<T>) {
  const [query, setQuery] = React.useState("");
  const [sort, setSort] = React.useState<SortState | null>(initialSort ?? null);
  const [page, setPage] = React.useState(1);

  React.useEffect(() => setPage(1), [query, rows]);

  const filtered = React.useMemo(() => {
    if (!query.trim()) return rows;
    const q = query.toLowerCase();
    return rows.filter((row) =>
      columns.some((col) => {
        const v = valueOf(row, col);
        return v != null && String(v).toLowerCase().includes(q);
      }),
    );
  }, [rows, columns, query]);

  const sorted = React.useMemo(() => {
    if (!sort) return filtered;
    const col = columns.find((c) => c.key === sort.key);
    if (!col) return filtered;
    const dir = sort.dir === "asc" ? 1 : -1;
    return [...filtered].sort((a, b) => compare(valueOf(a, col), valueOf(b, col)) * dir);
  }, [filtered, sort, columns]);

  const total = sorted.length;
  const usePaging = pageSize > 0;
  const pageCount = usePaging ? Math.max(1, Math.ceil(total / pageSize)) : 1;
  const current = usePaging ? Math.min(page, pageCount) : 1;
  const visible = usePaging ? sorted.slice((current - 1) * pageSize, current * pageSize) : sorted;

  const toggleSort = (col: Column<T>) => {
    if (!col.sortable) return;
    setSort((prev) =>
      prev?.key === col.key
        ? { key: col.key, dir: prev.dir === "asc" ? "desc" : "asc" }
        : { key: col.key, dir: "asc" },
    );
  };

  const alignClass = (a?: string) =>
    a === "right" ? "text-right" : a === "center" ? "text-center" : "text-left";

  return (
    <div className="space-y-3">
      {(searchable || toolbar) && (
        <div className="flex flex-wrap items-center gap-2">
          {toolbar}
          {searchable && (
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={searchPlaceholder}
              aria-label="Search table"
              className="ml-auto w-full max-w-xs rounded-[12px] border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-sm outline-none focus:border-[var(--accent)]"
            />
          )}
        </div>
      )}

      <div className="overflow-auto rounded-[20px] border border-[var(--border)] bg-[var(--card)] shadow-[var(--shadow-sm)]">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide text-[var(--foreground-secondary)]">
              {columns.map((col) => {
                const active = sort?.key === col.key;
                return (
                  <th
                    key={col.key}
                    className={`px-4 py-3 font-medium ${alignClass(col.align)} ${
                      col.sortable ? "cursor-pointer select-none" : ""
                    } ${col.className ?? ""}`}
                    onClick={() => toggleSort(col)}
                    aria-sort={active ? (sort!.dir === "asc" ? "ascending" : "descending") : "none"}
                    scope="col"
                  >
                    <span className="inline-flex items-center gap-1">
                      {col.header}
                      {col.sortable && (
                        <span className="text-[10px] opacity-60">
                          {active ? (sort!.dir === "asc" ? "▲" : "▼") : "↕"}
                        </span>
                      )}
                    </span>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-10 text-center text-[var(--foreground-secondary)]">
                  Loading…
                </td>
              </tr>
            ) : visible.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-10 text-center text-[var(--foreground-secondary)]">
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              visible.map((row) => (
                <tr
                  key={rowKey(row)}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                  className={`border-b border-[var(--border)] last:border-0 ${
                    onRowClick ? "cursor-pointer hover:bg-[var(--background-secondary)]" : ""
                  }`}
                >
                  {columns.map((col) => (
                    <td key={col.key} className={`px-4 py-3 ${alignClass(col.align)} ${col.className ?? ""}`}>
                      {col.render ? col.render(row) : String(valueOf(row, col) ?? "—")}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {usePaging && total > pageSize && (
        <div className="flex items-center justify-between text-sm text-[var(--foreground-secondary)]">
          <span>
            {(current - 1) * pageSize + 1}–{Math.min(current * pageSize, total)} of {total}
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={current <= 1}
              className="rounded-[10px] border border-[var(--border)] px-3 py-1 disabled:opacity-40"
            >
              Prev
            </button>
            <span>
              {current} / {pageCount}
            </span>
            <button
              type="button"
              onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
              disabled={current >= pageCount}
              className="rounded-[10px] border border-[var(--border)] px-3 py-1 disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
