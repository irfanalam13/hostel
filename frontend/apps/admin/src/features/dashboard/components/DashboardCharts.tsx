"use client";

import React from "react";
import type { HostelState } from "@/features/hostels/types";
import type { OwnerDashboardResponse } from "../types";
import { DashboardAnalytics } from "./DashboardAnalytics";
import { DashboardWidgets } from "./DashboardWidgets";

type Props = {
  state: HostelState;
  apiData?: OwnerDashboardResponse;
  /** Optional banner rendered between the analytics and widget blocks. */
  errorSlot?: React.ReactNode;
};

/**
 * Single recharts-backed boundary for the dashboard. Both chart blocks live
 * behind one dynamic import (see dashboard/page.tsx) so the heavy recharts
 * bundle is fetched once, on demand, rather than duplicated across two separate
 * lazy chunks.
 */
export function DashboardCharts({ state, apiData, errorSlot }: Props) {
  return (
    <>
      <DashboardAnalytics state={state} apiData={apiData} />
      {errorSlot}
      <DashboardWidgets state={state} />
    </>
  );
}
