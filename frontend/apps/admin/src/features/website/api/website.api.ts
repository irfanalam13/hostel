import { apiFetch } from "@hostel/api";

/** Field kinds the generic section editor knows how to render. */
export type FieldKind = "text" | "textarea" | "image" | "url" | "boolean" | "number";
export type FieldSchema = Record<string, FieldKind | { kind: "list"; fields: Record<string, FieldKind> }>;

export type SectionTypeInfo = { label: string; fields: FieldSchema; recommended: boolean };

export type WebsiteSection = {
  id: string;
  type: string;
  order: number;
  is_visible: boolean;
  content: Record<string, unknown>;
};

export type WebsiteSettings = {
  is_published: boolean;
  published_at: string | null;
  published_version: number;
  workspace_url: string;
  theme: Record<string, unknown>;
  seo: Record<string, string>;
  branding: Record<string, string>;
  navigation: Record<string, unknown>;
  footer: Record<string, unknown>;
  social: Record<string, string>;
  sections: WebsiteSection[];
  section_types: Record<string, SectionTypeInfo>;
};

export type WebsiteOverview = {
  is_published: boolean;
  published_at: string | null;
  published_version: number;
  has_unpublished_changes: boolean;
  section_count: number;
  visible_section_count: number;
  missing_sections: string[];
  seo_score: number;
  seo_checks: Record<string, boolean>;
  inquiry_count: number;
  new_inquiry_count: number;
  version_count: number;
};

export type WebsiteVersion = {
  number: number;
  note: string;
  published_by: string | null;
  created_at: string;
};

export type WebsiteInquiry = {
  id: string;
  name: string;
  email: string;
  phone: string;
  room_interest: string;
  message: string;
  status: "new" | "read" | "archived";
  created_at: string;
};

export type WebsiteMedia = {
  id: string;
  file: string;
  url: string;
  kind: "image" | "document";
  alt_text: string;
  created_at: string;
};

export const websiteApi = {
  settings: () => apiFetch<WebsiteSettings>("/website/settings/"),
  updateSettings: (payload: Partial<Pick<WebsiteSettings,
    "theme" | "seo" | "branding" | "navigation" | "footer" | "social">>) =>
    apiFetch<WebsiteSettings>("/website/settings/", {
      method: "PATCH", body: JSON.stringify(payload),
    }),
  overview: () => apiFetch<WebsiteOverview>("/website/overview/"),

  addSection: (type: string) =>
    apiFetch<WebsiteSection>("/website/sections/", {
      method: "POST", body: JSON.stringify({ type, content: {} }),
    }),
  updateSection: (id: string, payload: Partial<Pick<WebsiteSection, "content" | "is_visible">>) =>
    apiFetch<WebsiteSection>(`/website/sections/${id}/`, {
      method: "PATCH", body: JSON.stringify(payload),
    }),
  deleteSection: (id: string) =>
    apiFetch<void>(`/website/sections/${id}/`, { method: "DELETE" }),
  duplicateSection: (id: string) =>
    apiFetch<WebsiteSection>(`/website/sections/${id}/duplicate/`, { method: "POST" }),
  reorderSections: (order: string[]) =>
    apiFetch<WebsiteSection[]>("/website/sections/reorder/", {
      method: "POST", body: JSON.stringify({ order }),
    }),

  publish: (note = "") =>
    apiFetch<{ detail: string; version: number }>("/website/publish/", {
      method: "POST", body: JSON.stringify({ note }),
    }),
  unpublish: () => apiFetch<{ detail: string }>("/website/unpublish/", { method: "POST" }),
  versions: () => apiFetch<WebsiteVersion[]>("/website/versions/"),
  restoreVersion: (number: number) =>
    apiFetch<{ detail: string }>(`/website/versions/${number}/restore/`, { method: "POST" }),

  inquiries: (status?: string) =>
    apiFetch<WebsiteInquiry[] | { results: WebsiteInquiry[] }>("/website/inquiries/", {
      params: status ? { status } : undefined,
    }),
  updateInquiry: (id: string, status: WebsiteInquiry["status"]) =>
    apiFetch<WebsiteInquiry>(`/website/inquiries/${id}/`, {
      method: "PATCH", body: JSON.stringify({ status }),
    }),

  uploadMedia: (file: File, altText = "") => {
    const form = new FormData();
    form.append("file", file);
    form.append("alt_text", altText);
    return apiFetch<WebsiteMedia>("/website/media/", { method: "POST", body: form });
  },
};

export function unwrapList<T>(payload: T[] | { results: T[] }): T[] {
  return Array.isArray(payload) ? payload : payload?.results ?? [];
}
