// src/features/backups/components/BackupList.tsx
"use client";

import React from "react";
import type { BackupSnapshot } from "@/features/backups/types/backups.types";
import { downloadBackup } from "@/features/backups/api/backups.api";

function hostelLabel(h: BackupSnapshot["hostel"]) {
  if (typeof h === "string") return `Hostel #${h}`;
  const name = h?.name || "";
  const code = h?.code ? ` (${h.code})` : "";
  return `${name || `Hostel #${h.id}`}${code}`;
}

export function BackupList({
  items,
  loading,
  error,
  onRefresh,
}: {
  items: BackupSnapshot[];
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
}) {
  return (
    <div className="rounded-xl border p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold">Snapshots</h2>
        <button className="rounded-md border px-3 py-1.5 text-sm" onClick={onRefresh}>
          Refresh
        </button>
      </div>

      {loading && <p className="mt-3 text-sm text-gray-600">Loading…</p>}
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

      {!loading && !error && items.length === 0 && (
        <p className="mt-3 text-sm text-gray-600">No backups found.</p>
      )}

      {!loading && !error && items.length > 0 && (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b text-left">
                <th className="py-2">ID</th>
                <th className="py-2">Hostel</th>
                <th className="py-2">Kind</th>
                <th className="py-2">Note</th>
                <th className="py-2">Created</th>
                <th className="py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((s) => (
                <tr key={s.id} className="border-b">
                  <td className="py-2">{s.id}</td>
                  <td className="py-2">{hostelLabel(s.hostel)}</td>
                  <td className="py-2">{s.kind}</td>
                  <td className="py-2">{s.note || "-"}</td>
                  <td className="py-2">{s.created_at || s.created || "-"}</td>
                  <td className="py-2">
                    <button
                      className="rounded-md border px-3 py-1.5 text-sm"
                      onClick={async () => {
                        await downloadBackup(s.id);
                      }}
                    >
                      Download
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
