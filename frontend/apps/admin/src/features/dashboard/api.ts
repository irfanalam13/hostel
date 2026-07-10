import { apiFetch } from "@hostel/api";
import type { OwnerDashboardResponse } from "./types";

export function getOwnerDashboard() {
  return apiFetch<OwnerDashboardResponse>("/dashboard/owner/");
}