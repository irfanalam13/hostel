/**
 * Trusted Types — client-side default policy.
 *
 * The middleware ships `require-trusted-types-for 'script'` in REPORT-ONLY mode.
 * Installing a `default` policy here means that when a string reaches a DOM
 * injection sink (innerHTML, script src, …) the browser routes it through this
 * policy instead of refusing/spamming reports — giving us one auditable place to
 * sanitise and a safe migration path to full enforcement (CSP_TT_ENFORCE=1).
 *
 * Today the app renders through React (which escapes by default) and never sets
 * raw innerHTML, so the HTML/script branches are conservative pass-throughs. The
 * createScriptURL branch is the one that adds real protection: it only permits
 * same-origin / relative script URLs. Wire DOMPurify into `createHTML` if/when
 * the app starts rendering untrusted HTML.
 *
 * Note: React's own hydration normalises attribute HTML through this default
 * policy's `createHTML` (normalizeHTML → diffHydratedProperties), so the sink
 * fires on every render — we deliberately do NOT warn there, as it is expected,
 * React-controlled, and already escaped (warning on it was pure console noise).
 */

declare global {
  interface Window {
    trustedTypes?: {
      createPolicy: (name: string, rules: Record<string, (input: string) => string>) => unknown;
      defaultPolicy?: unknown;
    };
  }
}

let installed = false;

function isSameOrigin(url: string): boolean {
  try {
    // Relative URLs resolve against the document origin → same-origin.
    const u = new URL(url, window.location.href);
    return u.origin === window.location.origin;
  } catch {
    return false;
  }
}

export function installTrustedTypes(): void {
  if (installed) return;
  if (typeof window === "undefined") return;
  const tt = window.trustedTypes;
  if (!tt || typeof tt.createPolicy !== "function") return; // unsupported browser
  installed = true;

  try {
    tt.createPolicy("default", {
      // Pass-through: React escapes its output and never sets untrusted raw
      // HTML. React's hydration routes normal attribute HTML through here, so
      // this is a hot, expected path — no per-call warning (it was just noise).
      createHTML: (input: string) => input,
      createScript: (input: string) => input,
      createScriptURL: (input: string) => {
        if (isSameOrigin(input)) return input;
        // Block off-origin script URLs outright — there is no legitimate case
        // in this app, and this is the classic script-injection vector.
        throw new TypeError(`[trusted-types] blocked cross-origin script URL: ${input}`);
      },
    });
  } catch {
    // A 'default' policy may already exist (e.g. installed by a framework chunk);
    // that's fine — Trusted Types is still active.
  }
}
