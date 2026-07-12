import { PRICING, type PricingTier } from "./content";

/**
 * Dynamic pricing for the landing page.
 *
 * Plans (and any discount the admin sets) live in the backend and are served
 * unauthenticated from `/tenants/plans/public/`. We fetch them server-side so
 * the prices ship in the initial HTML (good for SEO) yet stay current via ISR.
 *
 * If the backend is unreachable or returns nothing (e.g. during a build with no
 * API, or a cold environment), we fall back to the static PRICING copy so the
 * page is never broken or empty.
 */

type PublicPlan = {
  id: number | string;
  name: string;
  description?: string;
  features?: unknown;
  period?: string;
  currency?: string;
  price_monthly: string | number;
  discounted_price: string | number;
  discount_percent: string | number;
  discount_label?: string;
  discount_live?: boolean;
  cta_label?: string;
  cta_href?: string;
  is_featured?: boolean;
  sort_order?: number;
};

function apiBase(): string {
  return (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api").replace(/\/+$/, "");
}

function formatPrice(amount: number, currency: string): string {
  if (!amount || amount <= 0) return "Free";
  return `${currency} ${amount.toLocaleString()}`;
}

function mapPlanToTier(p: PublicPlan): PricingTier {
  const currency = p.currency || "Rs.";
  const base = Number(p.price_monthly) || 0;
  const discounted = Number(p.discounted_price) || 0;
  const live = !!p.discount_live && base > 0 && discounted < base;
  const pct = Math.round(Number(p.discount_percent) || 0);

  return {
    name: p.name,
    // When a discount is live, the headline price is the discounted one and the
    // original is struck through next to it.
    price: formatPrice(live ? discounted : base, currency),
    originalPrice: live ? formatPrice(base, currency) : undefined,
    discountLabel: live ? (p.discount_label?.trim() || `${pct}% off`) : undefined,
    period: base > 0 ? p.period || "per hostel / month" : undefined,
    description: p.description || "",
    features: Array.isArray(p.features) ? (p.features as string[]) : [],
    cta: { label: p.cta_label || "Get started", href: p.cta_href || "/signup" },
    featured: !!p.is_featured,
  };
}

export async function getPricingTiers(): Promise<PricingTier[]> {
  try {
    const res = await fetch(`${apiBase()}/tenants/plans/public/`, {
      // Re-fetch at most every 5 minutes so admin price/discount changes appear
      // without a redeploy, while keeping the page effectively static.
      next: { revalidate: 300 },
      // Fail fast if the backend is cold/asleep so a slow API can't hang the
      // server render — fall back to static PRICING instead of a blank page.
      signal: AbortSignal.timeout(3500),
    });
    if (!res.ok) return PRICING;

    const json: unknown = await res.json();
    // Tolerate the API's {success, data} envelope, a {results} page, or a raw list.
    const list = (
      Array.isArray(json)
        ? json
        : (json as { data?: unknown; results?: unknown })?.data ??
          (json as { results?: unknown })?.results ??
          []
    ) as PublicPlan[];

    if (!Array.isArray(list) || list.length === 0) return PRICING;
    return list.map(mapPlanToTier);
  } catch {
    // Network/build-time failure — keep the marketing page working.
    return PRICING;
  }
}
