import { apiFetch } from "@hostel/api";

export type PlanSummary = {
  id: string;
  name: string;
  slug: string;
  description: string;
  price_monthly: string;
  price_yearly: string;
  discounted_price: string;
  currency: string;
  billing_interval: string;
  badge: string;
  is_recommended: boolean;
  is_featured: boolean;
};

export type UpgradeOptions = {
  feature: string | null;
  limit: string | null;
  current_plan: { id: string; name: string; slug: string } | null;
  plans: PlanSummary[];
};

export type Entitlements = {
  plan: { id: string; name: string; slug: string } | null;
  features: Record<string, boolean>;
  limits: Record<string, { max: number | null; used: number | null; remaining: number | null; unlimited: boolean }>;
};

export const subscriptionApi = {
  entitlements: () => apiFetch<Entitlements>("/subscriptions/entitlements/"),
  availablePlans: () => apiFetch<PlanSummary[]>("/subscriptions/plans/"),
  upgradeOptions: (params: { feature?: string; limit?: string; needed?: number }) =>
    apiFetch<UpgradeOptions>("/subscriptions/upgrade-options/", { params }),
};
