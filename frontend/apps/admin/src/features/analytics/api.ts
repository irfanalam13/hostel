import { api } from "@hostel/api";
import type { AnalyticsReport, AnalyticsTrends, TrendGranularity } from "./types";

/** Aggregated PWA analytics for the active hostel (owner/manager only). */
export async function getAnalyticsReport(days = 30): Promise<AnalyticsReport> {
  const res = await api.get<AnalyticsReport>("/analytics/report/", { params: { days } });
  return res.data;
}

/** Rollup-backed historical trends (super-admin only). */
export async function getAnalyticsTrends(
  days = 90,
  granularity: TrendGranularity = "day",
): Promise<AnalyticsTrends> {
  const res = await api.get<AnalyticsTrends>("/analytics/trends/", {
    params: { days, granularity },
  });
  return res.data;
}
