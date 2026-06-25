import { apiFetch } from "@/shared/api/apiClient";
import type { OwnerDashboardResponse } from "./types";

export function getOwnerDashboard() {
  return apiFetch<OwnerDashboardResponse>("/dashboard/owner/");
}