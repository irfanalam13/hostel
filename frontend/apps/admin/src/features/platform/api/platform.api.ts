import { apiFetch } from "@hostel/api";
import type {
  Analytics,
  Comparison,
  Feature,
  FeatureCategory,
  FeatureOverride,
  HostelSubscription,
  LimitDefinition,
  LimitOverride,
  Plan,
  PlanFeatureRow,
  PlanLimitRow,
  SubscriptionEvent,
} from "../types/platform.types";

function p<T>(path: string, options: RequestInit = {}) {
  return apiFetch<T>(`/platform${path}`, options);
}

const json = (body: unknown): RequestInit => ({ body: JSON.stringify(body) });

export const platformApi = {
  plans: {
    list: (search?: string) => p<Plan[]>(`/plans/${search ? `?search=${encodeURIComponent(search)}` : ""}`),
    retrieve: (id: string) => p<Plan>(`/plans/${id}/`),
    create: (body: Partial<Plan>) => p<Plan>("/plans/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<Plan>) =>
      p<Plan>(`/plans/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => p<void>(`/plans/${id}/`, { method: "DELETE" }),

    duplicate: (id: string, name?: string) =>
      p<Plan>(`/plans/${id}/duplicate/`, { method: "POST", ...json(name ? { name } : {}) }),
    archive: (id: string) => p<Plan>(`/plans/${id}/archive/`, { method: "POST", ...json({}) }),
    unarchive: (id: string) => p<Plan>(`/plans/${id}/unarchive/`, { method: "POST", ...json({}) }),
    activate: (id: string) => p<Plan>(`/plans/${id}/activate/`, { method: "POST", ...json({}) }),
    deactivate: (id: string) => p<Plan>(`/plans/${id}/deactivate/`, { method: "POST", ...json({}) }),

    features: (id: string) => p<PlanFeatureRow[]>(`/plans/${id}/features/`),
    setFeatures: (id: string, features: Record<string, boolean>, force = false) =>
      p<PlanFeatureRow[]>(`/plans/${id}/features/`, { method: "PUT", ...json({ features, force }) }),
    limits: (id: string) => p<PlanLimitRow[]>(`/plans/${id}/limits/`),
    setLimits: (
      id: string,
      limits: Record<string, { value: number; is_unlimited: boolean }>,
    ) => p<PlanLimitRow[]>(`/plans/${id}/limits/`, { method: "PUT", ...json({ limits }) }),

    comparison: () => p<Comparison>("/plans/comparison/"),
    reorder: (items: { id: string; sort_order: number }[]) =>
      p<{ updated: number }>("/plans/reorder/", { method: "POST", ...json(items) }),
    bulk: (ids: string[], action: string) =>
      p<{ action: string; count: number }>("/plans/bulk/", { method: "POST", ...json({ ids, action }) }),
    export: () => p<{ plans: unknown[] }>("/plans/export/"),
    import: (plans: unknown[]) =>
      p<{ created: number; updated: number }>("/plans/import/", { method: "POST", ...json({ plans }) }),
  },

  features: {
    list: () => p<Feature[]>("/features/"),
    create: (body: Partial<Feature>) => p<Feature>("/features/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<Feature>) =>
      p<Feature>(`/features/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => p<void>(`/features/${id}/`, { method: "DELETE" }),
  },

  categories: {
    list: () => p<FeatureCategory[]>("/feature-categories/"),
    create: (body: Partial<FeatureCategory>) =>
      p<FeatureCategory>("/feature-categories/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<FeatureCategory>) =>
      p<FeatureCategory>(`/feature-categories/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => p<void>(`/feature-categories/${id}/`, { method: "DELETE" }),
  },

  limits: {
    list: () => p<LimitDefinition[]>("/limit-definitions/"),
    create: (body: Partial<LimitDefinition>) =>
      p<LimitDefinition>("/limit-definitions/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<LimitDefinition>) =>
      p<LimitDefinition>(`/limit-definitions/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => p<void>(`/limit-definitions/${id}/`, { method: "DELETE" }),
  },

  featureOverrides: {
    list: () => p<FeatureOverride[]>("/feature-overrides/"),
    create: (body: Partial<FeatureOverride>) =>
      p<FeatureOverride>("/feature-overrides/", { method: "POST", ...json(body) }),
    remove: (id: string) => p<void>(`/feature-overrides/${id}/`, { method: "DELETE" }),
  },

  limitOverrides: {
    list: () => p<LimitOverride[]>("/limit-overrides/"),
    create: (body: Partial<LimitOverride>) =>
      p<LimitOverride>("/limit-overrides/", { method: "POST", ...json(body) }),
    remove: (id: string) => p<void>(`/limit-overrides/${id}/`, { method: "DELETE" }),
  },

  analytics: () => p<Analytics>("/analytics/"),

  subscriptions: {
    list: (search?: string) =>
      p<HostelSubscription[]>(`/subscriptions/${search ? `?search=${encodeURIComponent(search)}` : ""}`),
    assign: (hostel: string, plan: string, reason?: string) =>
      p<HostelSubscription>("/subscriptions/", { method: "POST", ...json({ hostel, plan, reason }) }),
    history: (hostelId: string) => p<SubscriptionEvent[]>(`/subscriptions/${hostelId}/history/`),
  },
};
