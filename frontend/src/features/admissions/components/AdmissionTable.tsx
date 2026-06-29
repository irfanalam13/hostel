"use client";

import { Table } from "@/shared/ui/Table";
import { EmptyState } from "@/shared/ui/EmptyState";
import type { AdmissionRequest } from "../types";
import { AdmissionStatusBadge } from "./AdmissionStatusBadge";

export function AdmissionTable({
  rows,
  loading,
  selected,
  onToggle,
  onToggleAll,
  onOpen,
}: {
  rows: AdmissionRequest[];
  loading: boolean;
  selected: Set<string>;
  onToggle: (id: string) => void;
  onToggleAll: (checked: boolean) => void;
  onOpen: (row: AdmissionRequest) => void;
}) {
  const allSelected = rows.length > 0 && rows.every((r) => selected.has(r.id));

  if (!rows.length && !loading) {
    return (
      <EmptyState
        title="No admission applications"
        description="Create a new application or adjust your filters."
        icon="📝"
      />
    );
  }

  return (
    <Table>
      <thead>
        <tr className="border-b text-left">
          <th className="p-3">
            <input
              type="checkbox"
              checked={allSelected}
              onChange={(e) => onToggleAll(e.target.checked)}
              aria-label="Select all"
            />
          </th>
          <th className="p-3">Application</th>
          <th className="p-3">Applicant</th>
          <th className="p-3">Education</th>
          <th className="p-3">District</th>
          <th className="p-3">Bed</th>
          <th className="p-3">Status</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr
            key={row.id}
            className="cursor-pointer border-b hover:bg-[var(--background-secondary)]"
            onClick={() => onOpen(row)}
          >
            <td className="p-3" onClick={(e) => e.stopPropagation()}>
              <input
                type="checkbox"
                checked={selected.has(row.id)}
                onChange={() => onToggle(row.id)}
                aria-label={`Select ${row.full_name}`}
              />
            </td>
            <td className="p-3">
              <div className="font-mono text-xs font-medium">{row.application_number || "-"}</div>
              <div className="text-xs text-[var(--muted)]">{row.application_date}</div>
            </td>
            <td className="p-3">
              <div className="font-medium">{row.full_name}</div>
              <div className="text-xs text-[var(--muted)]">{row.phone}</div>
            </td>
            <td className="p-3 text-sm">
              <div>{row.educational_institute || "-"}</div>
              <div className="text-xs text-[var(--muted)]">{row.current_level}</div>
            </td>
            <td className="p-3 text-sm">{row.district || "-"}</td>
            <td className="p-3 text-sm">{row.approved_bed_code || row.preferred_bed_code || "-"}</td>
            <td className="p-3">
              <AdmissionStatusBadge status={row.status} />
            </td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}
