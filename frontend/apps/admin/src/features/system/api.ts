import { api } from "@hostel/api";
import type { HeartbeatPayload, SystemStatus } from "./types";

/** Report this client's presence + PWA state. Best-effort; never throws. */
export async function sendHeartbeat(payload: HeartbeatPayload): Promise<void> {
  try {
    await api.post("/dashboard/heartbeat/", payload);
  } catch {
    /* offline / unauthenticated — ignore */
  }
}

/** Tenant-wide system status (owner/manager only — 403 otherwise). */
export async function getSystemStatus(): Promise<SystemStatus> {
  const res = await api.get<SystemStatus>("/dashboard/system-status/");
  return res.data;
}
