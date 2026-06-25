import { apiFetch } from "@/shared/api/apiClient";
import type {
  Hostel,
  HostelCreateInput,
  Plan,
  Subscription,
  SubscriptionCreateInput,
} from "../types/tenants.types";

function request<T>(path: string, options: RequestInit = {}, token?: string | null) {
  return apiFetch<T>(`/tenants${path}`, {
    ...options,
    auth: token ? false : undefined,
    headers: {
      ...(options.headers || {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
}

export const tenantsApi = {
  plans: {
    list: () => request<Plan[]>("/plans/"),
    retrieve: (id: string) => request<Plan>(`/plans/${id}/`),
  },

  hostels: {
    list: () => request<Hostel[]>("/hostels/"),
    retrieve: (id: string) => request<Hostel>(`/hostels/${id}/`),
    create: (payload: HostelCreateInput) =>
      request<Hostel>("/hostels/", { method: "POST", body: JSON.stringify(payload) }),
    update: (id: string, payload: Partial<HostelCreateInput>) =>
      request<Hostel>(`/hostels/${id}/`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    remove: (id: string) => request<void>(`/hostels/${id}/`, { method: "DELETE" }),
  },

  subscriptions: {
    list: (token?: string | null) => request<Subscription[]>("/subscriptions/", {}, token),
    retrieve: (id: string, token?: string | null) =>
      request<Subscription>(`/subscriptions/${id}/`, {}, token),
    create: (payload: SubscriptionCreateInput, token?: string | null) =>
      request<Subscription>(
        "/subscriptions/",
        { method: "POST", body: JSON.stringify(payload) },
        token
      ),
    update: (
      id: string,
      payload: Partial<SubscriptionCreateInput>,
      token?: string | null
    ) =>
      request<Subscription>(
        `/subscriptions/${id}/`,
        { method: "PATCH", body: JSON.stringify(payload) },
        token
      ),
    remove: (id: string, token?: string | null) =>
      request<void>(`/subscriptions/${id}/`, { method: "DELETE" }, token),
  },
};
