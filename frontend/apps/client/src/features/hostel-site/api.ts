/**
 * Server-side fetch of a workspace's published website.
 *
 * Called from the root page when the request arrived on a workspace host
 * (the edge proxy stamps `x-workspace` from the Host header). Cached briefly
 * via ISR so publishes appear fast while renders stay cheap; failures return
 * a typed status instead of throwing so the page can render a friendly state.
 */

export type SitePayload = {
  workspace: { name: string; username: string; url: string; public_url?: string };
  white_label?: {
    enabled?: boolean; platform_name?: string; browser_title?: string;
    footer_text?: string; hide_platform_branding?: boolean;
  };
  published: boolean;
  published_at?: string | null;
  version: number;
  theme: Record<string, unknown>;
  seo: Record<string, string>;
  branding: Record<string, string>;
  navigation: { items?: { label: string; href: string; visible?: boolean }[]; show_login?: boolean };
  footer: { about_text?: string; quick_links?: { label: string; href: string }[]; copyright?: string };
  social: Record<string, string>;
  sections: { id: string; type: string; order: number; content: Record<string, unknown> }[];
};

export type SiteResult =
  | { status: "ok"; site: SitePayload }
  | { status: "unpublished" }
  | { status: "not_found" }
  | { status: "blocked"; code: string }   // suspended / expired / disabled
  | { status: "error" };

function apiBase(): string {
  // Server-side fetch: inside Docker the browser-facing URL (localhost:8000)
  // points at the wrong container, so an internal service URL takes priority.
  // On Vercel/Render the public URL is reachable from the server too, so the
  // NEXT_PUBLIC fallback is correct there.
  return (
    process.env.API_INTERNAL_URL ||
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    "http://localhost:8000/api"
  ).replace(/\/+$/, "");
}

export type SiteIdentifier =
  | { workspace: string }        // default host: everest.myhostel.com
  | { tenantHost: string };      // custom domain: hostel.everest.com (Prompt 05)

export async function getPublicWebsite(id: SiteIdentifier): Promise<SiteResult> {
  const headers: Record<string, string> =
    "workspace" in id ? { "X-Workspace": id.workspace } : { "X-Tenant-Host": id.tenantHost };
  try {
    const res = await fetch(`${apiBase()}/website/public/`, {
      headers,
      // Publishes show within a minute; renders stay effectively static.
      next: { revalidate: 60 },
      signal: AbortSignal.timeout(5000),
    });

    if (res.ok) {
      const json = (await res.json()) as { data?: SitePayload } | SitePayload;
      const site = (json as { data?: SitePayload }).data ?? (json as SitePayload);
      if (site && Array.isArray(site.sections)) return { status: "ok", site };
      return { status: "error" };
    }

    const body = (await res.json().catch(() => null)) as
      | { meta?: { code?: string }; data?: { code?: string }; code?: string; detail?: string }
      | null;
    const code =
      body?.meta?.code || (body as { code?: string })?.code || (body?.data as { code?: string })?.code || "";

    if (code === "website_unpublished" || (res.status === 404 && !code)) {
      // Distinguish "workspace exists, site offline" from "no such workspace".
      return code === "website_unpublished" ? { status: "unpublished" } : { status: "not_found" };
    }
    if (code === "workspace_not_found") return { status: "not_found" };
    if (code.startsWith("workspace_")) return { status: "blocked", code };
    return { status: "error" };
  } catch {
    return { status: "error" };
  }
}
