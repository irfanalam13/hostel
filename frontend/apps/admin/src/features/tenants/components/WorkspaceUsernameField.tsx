"use client";

import React from "react";
import { Input } from "@hostel/ui";
import { normalizeWorkspaceUsername, tenantBaseDomain } from "@hostel/utils";
import {
  useWorkspaceAvailability,
  type AvailabilityState,
} from "../hooks/useWorkspaceAvailability";

type Props = {
  value: string;
  onChange: (value: string) => void;
  /** Notified whenever the availability state changes (for submit gating). */
  onStateChange?: (state: AvailabilityState) => void;
  disabled?: boolean;
};

/**
 * Workspace-username input with live availability checking.
 *
 * Shows the resulting workspace URL (everest.myhostel.com), an inline
 * available/taken indicator, and one-click suggestions when the name is
 * taken. The username is permanent after signup, and the copy says so.
 */
export function WorkspaceUsernameField({ value, onChange, onStateChange, disabled }: Props) {
  const availability = useWorkspaceAvailability(value);
  const base = tenantBaseDomain();

  const lastReported = React.useRef<AvailabilityState | null>(null);
  React.useEffect(() => {
    if (lastReported.current !== availability) {
      lastReported.current = availability;
      onStateChange?.(availability);
    }
  }, [availability, onStateChange]);

  const indicator = (() => {
    switch (availability.status) {
      case "checking":
        return <span className="text-gray-500">Checking…</span>;
      case "available":
        return <span className="text-green-600 font-medium">✓ Available</span>;
      case "taken":
        return <span className="text-red-600 font-medium">Already taken</span>;
      case "invalid":
        return <span className="text-red-600">{availability.message}</span>;
      case "error":
        return <span className="text-amber-600">{availability.message}</span>;
      default:
        return null;
    }
  })();

  return (
    <div>
      <Input
        id="workspace_username"
        name="workspace_username"
        label="Workspace Username"
        value={value}
        onChange={(e) => {
          // Normalize as the user types: lowercase, strip anything illegal.
          const cleaned = e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, "").slice(0, 32);
          onChange(cleaned);
        }}
        required
        autoComplete="off"
        spellCheck={false}
        disabled={disabled}
        aria-describedby="workspace_username_hint"
      />

      <div id="workspace_username_hint" className="mt-1 text-xs text-gray-600">
        Your workspace URL:{" "}
        <span className="font-mono font-semibold text-gray-800">
          {normalizeWorkspaceUsername(value) || "your-hostel"}.{base}
        </span>
        <span className="block text-gray-400">
          Lowercase letters, numbers and hyphens. This is permanent — it can&apos;t be changed
          later (your hostel&apos;s display name can).
        </span>
      </div>

      {indicator && <div className="mt-1 text-xs">{indicator}</div>}

      {availability.status === "taken" && availability.suggestions.length > 0 && (
        <div className="mt-2 text-xs text-gray-600">
          <span className="mr-1">Try:</span>
          {availability.suggestions.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => onChange(s)}
              className="mr-1 mb-1 inline-block rounded-full border border-gray-300 px-2 py-0.5 font-mono hover:border-blue-500 hover:text-blue-600"
            >
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
