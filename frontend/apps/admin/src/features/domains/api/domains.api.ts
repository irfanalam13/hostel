import { apiFetch } from "@hostel/api";

export type DnsRecord = { type: string; host: string; value: string };

export type CustomDomain = {
  id: string;
  domain: string;
  status: "pending" | "verified" | "active" | "failed" | "disabled";
  is_primary: boolean;
  verification_method: string;
  verified_at: string | null;
  last_checked_at: string | null;
  last_error: string;
  ssl_status: "unknown" | "pending" | "active" | "expiring" | "expired" | "error";
  ssl_expires_at: string | null;
  dns_health: { txt?: boolean; cname?: boolean; checked_at?: string };
  records: { txt: DnsRecord; cname: DnsRecord };
  url: string;
  created_at: string;
};

export type DomainListing = {
  workspace_url: string;
  public_url: string;
  limit: number;
  domains: CustomDomain[];
};

export const domainsApi = {
  list: () => apiFetch<DomainListing>("/domains/"),
  add: (domain: string) =>
    apiFetch<CustomDomain>("/domains/", { method: "POST", body: JSON.stringify({ domain }) }),
  verify: (id: string) =>
    apiFetch<CustomDomain>(`/domains/${id}/verify/`, { method: "POST" }),
  activate: (id: string, makePrimary = true) =>
    apiFetch<CustomDomain>(`/domains/${id}/activate/`, {
      method: "POST", body: JSON.stringify({ make_primary: makePrimary }),
    }),
  setPrimary: (id: string) =>
    apiFetch<CustomDomain>(`/domains/${id}/primary/`, { method: "POST" }),
  disable: (id: string) =>
    apiFetch<CustomDomain>(`/domains/${id}/disable/`, { method: "POST" }),
  checkSsl: (id: string) =>
    apiFetch<CustomDomain>(`/domains/${id}/ssl/`, { method: "POST" }),
  remove: (id: string) => apiFetch<void>(`/domains/${id}/`, { method: "DELETE" }),
};
