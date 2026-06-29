import { api } from "@/shared/api/apiClient";
import type { AnalyticsReport } from "./types";

/** Aggregated PWA analytics for the active hostel (owner/manager only). */
export async function getAnalyticsReport(days = 30): Promise<AnalyticsReport> {
  const res = await api.get<AnalyticsReport>("/analytics/report/", { params: { days } });
  return res.data;
}
