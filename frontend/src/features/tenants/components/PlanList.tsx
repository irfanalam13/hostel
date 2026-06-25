"use client";

import React from "react";
import type { Plan } from "../types/tenants.types";

export function PlanList({ plans }: { plans: Plan[] }) {
  return (
    <div className="space-y-3">
      {plans.map((p) => (
        <div key={p.id} className="rounded-xl border border-zinc-200 bg-white p-4">
          <div className="flex items-center justify-between">
            <div className="font-semibold">{p.name}</div>
            {p.price_monthly !== undefined && (
              <div className="text-sm text-zinc-600">Rs {p.price_monthly}</div>
            )}
          </div>

          <div className="mt-2 grid grid-cols-2 gap-2 text-sm text-zinc-700">
            {"max_rooms" in p && <div>Max rooms: {String(p.max_rooms)}</div>}
            {"max_students" in p && <div>Max students: {String(p.max_students)}</div>}
          </div>
        </div>
      ))}
      {!plans.length && (
        <div className="rounded-xl border border-zinc-200 bg-white p-4 text-sm text-zinc-600">
          No plans found.
        </div>
      )}
    </div>
  );
}
