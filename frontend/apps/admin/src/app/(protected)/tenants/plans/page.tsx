"use client";

import React, { useEffect, useState } from "react";
import { tenantsApi } from "@/features/tenants/api/tenants.api";
import type { Plan } from "@/features/tenants/types/tenants.types";
import { PlanList } from "@/features/tenants/components/PlanList";

export default function PlansPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    tenantsApi.plans
      .list()
      .then(setPlans)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-semibold">Plans</h1>
      {error && <div className="text-sm text-red-600">{error}</div>}
      <PlanList plans={plans} />
    </div>
  );
}