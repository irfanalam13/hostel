"use client";

import { useEffect, useRef, useState } from "react";
import { normalizeWorkspaceUsername, validateWorkspaceUsername } from "@hostel/utils";
import { workspacesApi } from "../api/workspaces.api";

export type AvailabilityState = {
  /**
   * idle      — nothing to check yet (empty input)
   * invalid   — fails local rules (format/length/reserved); no API call made
   * checking  — request in flight
   * available — confirmed free by the API
   * taken     — confirmed taken by the API
   * error     — availability service unreachable (form may still submit;
   *             the backend re-validates on signup anyway)
   */
  status: "idle" | "invalid" | "checking" | "available" | "taken" | "error";
  message: string;
  suggestions: string[];
};

const IDLE: AvailabilityState = { status: "idle", message: "", suggestions: [] };

/**
 * Debounced, real-time workspace-username availability.
 *
 * Local validation runs instantly (mirrors the backend rules); only locally
 * valid values hit the API, debounced and abortable so fast typing produces
 * at most one in-flight request.
 */
export function useWorkspaceAvailability(username: string, debounceMs = 400): AvailabilityState {
  const [state, setState] = useState<AvailabilityState>(IDLE);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    abortRef.current?.abort();

    const value = normalizeWorkspaceUsername(username);
    if (!value) {
      setState(IDLE);
      return;
    }

    const check = validateWorkspaceUsername(value);
    if (!check.ok) {
      setState({ status: "invalid", message: check.message, suggestions: [] });
      return;
    }

    setState({ status: "checking", message: "", suggestions: [] });
    const controller = new AbortController();
    abortRef.current = controller;

    const timer = setTimeout(async () => {
      try {
        const result = await workspacesApi.checkAvailability(value, {
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        if (result.available) {
          setState({ status: "available", message: "", suggestions: [] });
        } else {
          setState({
            status: "taken",
            message: result.detail || "This workspace username is not available.",
            suggestions: result.suggestions || [],
          });
        }
      } catch {
        if (controller.signal.aborted) return;
        setState({
          status: "error",
          message: "Couldn't check availability — it will be verified on submit.",
          suggestions: [],
        });
      }
    }, debounceMs);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [username, debounceMs]);

  return state;
}
