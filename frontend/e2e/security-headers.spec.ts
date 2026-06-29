/**
 * Security header tests (Phase 10 hardening).
 *
 * Asserts the middleware emits a strict, nonce-based CSP plus the cross-origin
 * isolation + Permissions-Policy headers — AND that the app still renders, which
 * proves `'strict-dynamic'` didn't lock out Next's own scripts.
 */
import { test, expect } from "./support/fixtures";

test.describe("Security headers @smoke", () => {
  test("document carries a strict nonce-based CSP and isolation headers", async ({ page, mockApi }) => {
    await mockApi();
    const response = await page.goto("/login");
    expect(response, "navigation response").not.toBeNull();
    const h = response!.headers();

    const csp = h["content-security-policy"] || "";
    expect(csp, "CSP present").toContain("script-src");
    expect(csp, "per-request nonce").toMatch(/'nonce-[A-Za-z0-9+/=]+'/);
    expect(csp, "strict-dynamic").toContain("'strict-dynamic'");
    expect(csp).toContain("object-src 'none'");
    expect(csp).toContain("base-uri 'none'");
    expect(csp).toContain("frame-ancestors 'none'");

    // Cross-origin isolation.
    expect(h["cross-origin-opener-policy"]).toBe("same-origin");
    expect(h["cross-origin-embedder-policy"]).toBe("credentialless");
    expect(h["cross-origin-resource-policy"]).toBe("same-origin");

    // Locked-down feature policy + misc.
    expect(h["permissions-policy"] || "").toContain("camera=()");
    expect(h["x-content-type-options"]).toBe("nosniff");
    expect(h["referrer-policy"]).toBeTruthy();

    // Trusted Types rolled out report-only first.
    const cspRo = h["content-security-policy-report-only"] || "";
    expect(cspRo).toContain("require-trusted-types-for 'script'");

    // The strict CSP must not have broken the app's own scripts.
    await expect(page.getByRole("button", { name: /login/i })).toBeVisible();
  });

  test("each navigation gets a fresh CSP nonce", async ({ page, mockApi }) => {
    await mockApi();
    const r1 = await page.goto("/login");
    const r2 = await page.goto("/offline");
    const n1 = (r1!.headers()["content-security-policy"] || "").match(/'nonce-([^']+)'/)?.[1];
    const n2 = (r2!.headers()["content-security-policy"] || "").match(/'nonce-([^']+)'/)?.[1];
    expect(n1).toBeTruthy();
    expect(n2).toBeTruthy();
    expect(n1).not.toBe(n2);
  });
});
