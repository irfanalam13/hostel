"use client";

import React from "react";
import type { Subscription } from "../types/tenants.types";
import { Button } from "@hostel/ui";

export function SubscriptionList({
  subs,
  onDelete,
}: {
  subs: Subscription[];
  onDelete: (id: string) => Promise<void>;
}) {
  return (
    <div className="space-y-3">
      {subs.map((s) => (
        <div key={s.id} className="rounded-xl border border-zinc-200 bg-white p-4">
          <div className="flex items-center justify-between">
            <div className="font-semibold">Subscription #{s.id}</div>
            <Button type="button" onClick={() => onDelete(s.id)} className="px-3 py-2">
              Delete
            </Button>
          </div>

          <div className="mt-2 grid grid-cols-1 gap-2 text-sm text-zinc-700 md:grid-cols-4">
            <div>Hostel: {s.hostel}</div>
            <div>Plan: {s.plan}</div>
            <div>Start: {s.start_date}</div>
            <div>End: {s.end_date}</div>
          </div>
        </div>
      ))}

      {!subs.length && (
        <div className="rounded-xl border border-zinc-200 bg-white p-4 text-sm text-zinc-600">
          No subscriptions found (or auth missing).
        </div>
      )}
    </div>
  );
}
