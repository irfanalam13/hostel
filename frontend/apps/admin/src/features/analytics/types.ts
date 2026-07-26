// Mirrors backend/apps/analytics/services.py build_report().

export interface AnalyticsReport {
  window_days: number;
  total_events: number;
  install: { prompts: number; accepted: number; dismissed: number; installed: number; rate: number };
  update: { available: number; applied: number; rate: number };
  offline_usage: { sessions: number; total_seconds: number; users: number };
  feature_adoption: { name: string; uses: number; users: number }[];
  push: { received: number; opened: number; open_rate: number };
  cache: { hits: number; misses: number; efficiency: number };
  sync: { success: number; failure: number; success_rate: number };
  device_types: Record<string, number>;
  browsers: Record<string, number>;
  errors: { total: number; daily: Record<string, number> };
}

// Mirrors backend/apps/analytics/rollup.py build_trends() — served from the
// durable EventDailyRollup aggregation tier (not the transactional table).
export type TrendGranularity = "day" | "week" | "month";

export interface AnalyticsTrends {
  granularity: TrendGranularity;
  window_days: number;
  source: string;
  buckets: string[];
  series: Record<string, Record<string, number>>; // bucket -> event_type -> count
  totals: Record<string, number>; // event_type -> total
}
