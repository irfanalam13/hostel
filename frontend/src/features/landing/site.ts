import { FAQS, type Faq } from "./content";
import {
  PRIVACY_SECTIONS,
  TERMS_SECTIONS,
  SECURITY_SECTIONS,
  LAST_UPDATED,
} from "./legal";
import type { LegalSection } from "./components/LegalDocument";

/**
 * Backend-connected marketing content (FAQ, legal pages, About) + lead capture.
 *
 * All reads are server-side (SEO + ISR) with a graceful fallback to the original
 * static copy, so the public pages always render even if the API is unreachable
 * (cold env / build with no backend). Lead submission is client-side.
 */

function apiBase(): string {
  return (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api").replace(/\/+$/, "");
}

function unwrap<T>(json: unknown): T {
  if (json && typeof json === "object" && "data" in (json as Record<string, unknown>)) {
    return (json as { data: T }).data;
  }
  return json as T;
}

async function getJson<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${apiBase()}${path}`, { next: { revalidate: 300 } });
    if (!res.ok) return null;
    return unwrap<T>(await res.json());
  } catch {
    return null;
  }
}

/* -------------------------------- FAQ ---------------------------------- */
type ApiFaq = { id: number | string; question: string; answer: string };

export async function getFaqs(): Promise<Faq[]> {
  const list = await getJson<ApiFaq[]>("/marketing/faqs/");
  if (!list || !Array.isArray(list) || list.length === 0) return FAQS;
  return list.map((f) => ({ question: f.question, answer: f.answer }));
}

/* ------------------------------ Legal docs ----------------------------- */
export type LegalDoc = {
  slug: string;
  eyebrow: string;
  title: string;
  description: string;
  last_updated: string;
  sections: LegalSection[];
};

const STATIC_LEGAL: Record<string, LegalDoc> = {
  privacy: {
    slug: "privacy", eyebrow: "Legal", title: "Privacy Policy",
    description: "How we collect, use, and protect your information.",
    last_updated: LAST_UPDATED, sections: PRIVACY_SECTIONS,
  },
  terms: {
    slug: "terms", eyebrow: "Legal", title: "Terms of Service",
    description: "The terms that govern your use of the platform.",
    last_updated: LAST_UPDATED, sections: TERMS_SECTIONS,
  },
  security: {
    slug: "security", eyebrow: "Trust", title: "Security",
    description: "How we keep your data safe — access control, encryption, auditing and recovery.",
    last_updated: LAST_UPDATED, sections: SECURITY_SECTIONS,
  },
};

export async function getLegalDocument(slug: "privacy" | "terms" | "security"): Promise<LegalDoc> {
  const doc = await getJson<LegalDoc>(`/marketing/legal/${slug}/`);
  if (!doc || !Array.isArray(doc.sections) || doc.sections.length === 0) return STATIC_LEGAL[slug];
  return doc;
}

/* ------------------------------ Site pages ----------------------------- */
export type SitePageBlock =
  | { type: "prose"; heading: string; paragraphs: string[] }
  | { type: "cards"; items: { icon: string; title: string; description: string }[] };

export type SitePage = {
  slug: string;
  eyebrow: string;
  title: string;
  description: string;
  body: SitePageBlock[];
};

export async function getSitePage(slug: string): Promise<SitePage | null> {
  const page = await getJson<SitePage>(`/marketing/pages/${slug}/`);
  if (!page || !Array.isArray(page.body)) return null;
  return page;
}

/* ------------------------------- Leads --------------------------------- */
export type LeadInput = {
  name: string;
  email: string;
  organization?: string;
  message: string;
  kind?: "demo" | "sales" | "general";
};

export type LeadResult = { ok: boolean; message: string };

/** Submit a sales/demo enquiry (client-side). */
export async function submitLead(input: LeadInput): Promise<LeadResult> {
  try {
    const res = await fetch(`${apiBase()}/marketing/leads/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    });
    const body = await res.json().catch(() => null);
    if (res.ok) {
      const data = unwrap<{ detail?: string }>(body);
      return { ok: true, message: data?.detail || "Thanks! We'll be in touch shortly." };
    }
    if (res.status === 429) {
      return { ok: false, message: "Too many requests — please try again a bit later." };
    }
    const msg =
      (body && (body.message || body?.errors?.email?.[0] || body?.errors?.message?.[0])) ||
      "Something went wrong. Please try again.";
    return { ok: false, message: String(msg) };
  } catch {
    return { ok: false, message: "Network error — please try again." };
  }
}
