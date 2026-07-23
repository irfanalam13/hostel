// src/features/backups/components/HostelPicker.tsx
"use client";

import React from "react";

type Props = {
  hostelId: string | null;
  setHostelId: (v: string | null) => void;
};

export function HostelPicker({ hostelId, setHostelId }: Props) {
  return (
    <div className="flex items-end gap-3">
      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium">Hostel ID</label>
        <input
          className="w-40 rounded-md border px-3 py-2 text-sm"
          placeholder="Hostel UUID"
          value={hostelId ?? ""}
          onChange={(e) => {
            const v = e.target.value;
            setHostelId(v || null);
          }}
        />
        <p className="text-xs text-gray-500">
          Later you can replace this with a real hostel dropdown.
        </p>
      </div>
    </div>
  );
}
