"use client";

import React from "react";
import type { Hostel } from "../types/tenants.types";
import { formatDate, yesNo } from "../utils/tenants.helpers";
import { Button } from "@/shared/ui/Button";

export function HostelList({
  hostels,
  onDelete,
  onQuickToggleActive,
}: {
  hostels: Hostel[];
  onDelete: (id: string) => Promise<void>;
  onQuickToggleActive: (h: Hostel) => Promise<void>;
}) {
  return (
    <div className="space-y-3">
      {hostels.map((h) => (
        <div key={h.id} className="rounded-xl border border-zinc-200 bg-white p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="font-semibold">{h.name} <span className="text-zinc-500">({h.code})</span></div>
              <div className="text-sm text-zinc-600">
                Phone: {h.phone || "-"} • Address: {h.address || "-"}
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button
                type="button"
                onClick={() => onQuickToggleActive(h)}
                className="px-3 py-2"
              >
                {h.is_active ? "Disable" : "Enable"}
              </Button>
              <Button
                type="button"
                onClick={() => onDelete(h.id)}
                className="px-3 py-2"
              >
                Delete
              </Button>
            </div>
          </div>

          <div className="mt-3 grid grid-cols-1 gap-2 text-sm text-zinc-700 md:grid-cols-3">
            <div>Plan: {h.plan_name || "-"}</div>
            <div>Active until: {formatDate(h.subscription_active_until)}</div>
            <div>Active: {yesNo(h.is_active)}</div>
            <div>Created: {formatDate(h.created_at)}</div>
          </div>
        </div>
      ))}

      {!hostels.length && (
        <div className="rounded-xl border border-zinc-200 bg-white p-4 text-sm text-zinc-600">
          No hostels found.
        </div>
      )}
    </div>
  );
}
