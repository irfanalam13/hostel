/**
 * CSP / Trusted-Types violation collector.
 *
 * The middleware points `report-uri` + `report-to` here. Browsers POST either
 * the legacy `application/csp-report` shape or the Reporting API
 * `application/reports+json` array. We log a compact line server-side (picked up
 * by the platform's log drain / Sentry breadcrumb) and always return 204 so the
 * browser never retries. This is how we watch the Trusted-Types report-only
 * rollout before flipping CSP_TT_ENFORCE=1.
 */
import { NextResponse } from "next/server";

export const runtime = "nodejs";
// Never prerender/cache — this is a pure sink.
export const dynamic = "force-dynamic";

const MAX_BODY = 64 * 1024; // ignore oversized/abusive payloads

function summarize(report: unknown): Record<string, unknown> | null {
  if (!report || typeof report !== "object") return null;
  // Reporting API entry: { type, body: {...} }; legacy: { "csp-report": {...} }
  const body =
    (report as { body?: Record<string, unknown> }).body ??
    (report as { "csp-report"?: Record<string, unknown> })["csp-report"] ??
    (report as Record<string, unknown>);
  return {
    directive: body["effectiveDirective"] ?? body["violated-directive"],
    blocked: body["blockedURL"] ?? body["blocked-uri"],
    docURL: body["documentURL"] ?? body["document-uri"],
    sample: body["scriptSample"] ?? body["script-sample"],
    disposition: body["disposition"],
  };
}

export async function POST(req: Request) {
  try {
    const len = Number(req.headers.get("content-length") || 0);
    if (len > MAX_BODY) return new NextResponse(null, { status: 413 });

    const text = await req.text();
    if (text.length > MAX_BODY) return new NextResponse(null, { status: 413 });

    const parsed = JSON.parse(text);
    const reports = Array.isArray(parsed) ? parsed : [parsed];
    for (const r of reports.slice(0, 20)) {
      const s = summarize(r);
      if (s && (s.directive || s.blocked)) {
        // Keep it to one structured line; avoid logging full payloads (could
        // contain inline script samples that are themselves sensitive).
        console.warn("[csp-report]", JSON.stringify(s));
      }
    }
  } catch {
    /* malformed report — ignore */
  }
  return new NextResponse(null, { status: 204 });
}

// Some browsers preflight the report endpoint.
export async function OPTIONS() {
  return new NextResponse(null, { status: 204 });
}
