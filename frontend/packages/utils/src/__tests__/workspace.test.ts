import { describe, it, expect, beforeEach, afterEach } from "vitest";
import {
  extractWorkspaceFromHost,
  isPlatformHost,
  normalizeWorkspaceUsername,
  suggestWorkspaceUsername,
  validateWorkspaceUsername,
  workspaceStore,
  workspaceUrlFor,
} from "../workspace";

const ENV_KEYS = [
  "NEXT_PUBLIC_TENANT_BASE_DOMAIN",
  "NEXT_PUBLIC_TENANT_URL_SCHEME",
  "NEXT_PUBLIC_WORKSPACE_USERNAME_MIN_LENGTH",
  "NEXT_PUBLIC_WORKSPACE_USERNAME_MAX_LENGTH",
  "NEXT_PUBLIC_PLATFORM_HOSTS",
] as const;
const saved: Record<string, string | undefined> = {};

beforeEach(() => {
  for (const k of ENV_KEYS) saved[k] = process.env[k];
  localStorage.clear();
});

afterEach(() => {
  for (const k of ENV_KEYS) {
    if (saved[k] === undefined) delete process.env[k];
    else process.env[k] = saved[k];
  }
});

describe("normalizeWorkspaceUsername", () => {
  it("trims and lowercases", () => {
    expect(normalizeWorkspaceUsername("  EVEREST  ")).toBe("everest");
    expect(normalizeWorkspaceUsername("")).toBe("");
  });
});

describe("validateWorkspaceUsername (mirrors backend rules)", () => {
  it.each(["everest", "everest123", "everest-hostel", "ktm-hostel", "abc"])(
    "accepts %s",
    (v) => {
      expect(validateWorkspaceUsername(v)).toEqual({ ok: true, value: v });
    },
  );

  it.each([
    ["", "required"],
    ["ab", "too_short"],
    ["e".repeat(33), "too_long"],
    ["everest hostel", "invalid"],
    ["everest@", "invalid"],
    ["everest_hostel", "invalid"],
    ["-everest", "invalid"],
    ["everest-", "invalid"],
    ["éverest", "invalid"],
    ["admin", "reserved"],
    ["api", "reserved"],
    ["www", "reserved"],
  ] as const)("rejects %s (%s)", (value, reason) => {
    const res = validateWorkspaceUsername(value);
    expect(res.ok).toBe(false);
    if (!res.ok) expect(res.reason).toBe(reason);
  });

  it("normalizes before validating (Everest is fine)", () => {
    expect(validateWorkspaceUsername("  Everest ")).toEqual({ ok: true, value: "everest" });
  });

  it("respects configured length limits", () => {
    process.env.NEXT_PUBLIC_WORKSPACE_USERNAME_MIN_LENGTH = "5";
    const res = validateWorkspaceUsername("abcd");
    expect(res.ok).toBe(false);
    if (!res.ok) expect(res.reason).toBe("too_short");
  });
});

describe("suggestWorkspaceUsername", () => {
  it("slugifies a hostel name", () => {
    expect(suggestWorkspaceUsername("Everest International Hostel")).toBe(
      "everest-international-hostel",
    );
  });

  it("strips symbols and collapses separators", () => {
    expect(suggestWorkspaceUsername("  Ever est's  @Hostel!! ")).toBe("ever-ests-hostel");
  });

  it("returns empty for unusable input (caller decides fallback)", () => {
    expect(suggestWorkspaceUsername("@@@")).toBe("");
  });
});

describe("extractWorkspaceFromHost (mirrors backend middleware)", () => {
  beforeEach(() => {
    process.env.NEXT_PUBLIC_TENANT_BASE_DOMAIN = "myhostel.com";
  });

  it.each([
    ["everest.myhostel.com", "everest"],
    ["everest.myhostel.com:3000", "everest"],
    ["EVEREST.MYHOSTEL.COM", "everest"],
  ])("resolves %s -> %s", (host, slug) => {
    expect(extractWorkspaceFromHost(host)).toBe(slug);
  });

  it.each([
    "myhostel.com",          // root domain
    "www.myhostel.com",      // reserved -> behaves as root
    "api.myhostel.com",      // reserved
    "a.b.myhostel.com",      // nested subdomain
    "localhost",
    "127.0.0.1",
    "othersite.com",         // unrelated domain
    "evil-myhostel.com",     // suffix trick must not match
    "bad_label.myhostel.com" // invalid label
  ])("returns null for %s", (host) => {
    expect(extractWorkspaceFromHost(host)).toBeNull();
  });

  it("supports *.localhost for development", () => {
    process.env.NEXT_PUBLIC_TENANT_BASE_DOMAIN = "localhost";
    expect(extractWorkspaceFromHost("everest.localhost:3000")).toBe("everest");
    expect(extractWorkspaceFromHost("localhost:3000")).toBeNull();
  });

  it("never treats a *.vercel.app deployment host as a workspace", () => {
    // Base domain unset on Vercel -> defaults to "localhost"; the vercel.app
    // suffix must still be recognised as platform, not a tenant.
    delete process.env.NEXT_PUBLIC_TENANT_BASE_DOMAIN;
    expect(extractWorkspaceFromHost("hostel-ten-hazel.vercel.app")).toBeNull();
    expect(extractWorkspaceFromHost("my-app-git-main.vercel.app")).toBeNull();
  });
});

describe("isPlatformHost (custom-domain detection, Prompt 05)", () => {
  beforeEach(() => {
    process.env.NEXT_PUBLIC_TENANT_BASE_DOMAIN = "myhostel.com";
  });

  it.each(["myhostel.com", "everest.myhostel.com", "localhost", "localhost:3000",
           "everest.localhost:3000", "127.0.0.1", "testserver"])(
    "%s is a platform host", (host) => {
      expect(isPlatformHost(host)).toBe(true);
    },
  );

  it.each(["hostel.everest.com", "erp.everesthostel.edu.np", "portal.everest.com:443"])(
    "%s is a tenant custom domain", (host) => {
      expect(isPlatformHost(host)).toBe(false);
    },
  );

  it.each([
    "hostel-ten-hazel.vercel.app",
    "my-app-git-main.vercel.app",
    "vercel.app",
  ])("%s (Vercel deployment host) is a platform host", (host) => {
    // Even with the base domain unset (the Vercel default of "localhost").
    delete process.env.NEXT_PUBLIC_TENANT_BASE_DOMAIN;
    expect(isPlatformHost(host)).toBe(true);
  });

  it("honours NEXT_PUBLIC_PLATFORM_HOSTS for exact hosts and suffixes", () => {
    process.env.NEXT_PUBLIC_PLATFORM_HOSTS = "staging.example.dev, .preview.example.dev";
    expect(isPlatformHost("staging.example.dev")).toBe(true); // exact
    expect(isPlatformHost("pr-42.preview.example.dev")).toBe(true); // suffix
    expect(isPlatformHost("preview.example.dev")).toBe(true); // bare, via ".suffix"
    expect(isPlatformHost("hostel.everest.com")).toBe(false); // still a tenant domain
  });
});

describe("workspaceUrlFor", () => {
  it("builds https URLs on real domains", () => {
    process.env.NEXT_PUBLIC_TENANT_BASE_DOMAIN = "myhostel.com";
    expect(workspaceUrlFor("everest")).toBe("https://everest.myhostel.com");
  });

  it("builds http URLs on localhost", () => {
    process.env.NEXT_PUBLIC_TENANT_BASE_DOMAIN = "localhost";
    expect(workspaceUrlFor("everest")).toBe("http://everest.localhost");
  });
});

describe("workspaceStore", () => {
  it("persists and clears the workspace context", () => {
    workspaceStore.set({ slug: "everest", url: "https://everest.myhostel.com" });
    expect(workspaceStore.getSlug()).toBe("everest");
    workspaceStore.clear();
    expect(workspaceStore.getSlug()).toBeUndefined();
  });

  it("survives corrupted storage", () => {
    localStorage.setItem("workspace_context_v1", "{not json");
    expect(workspaceStore.get()).toEqual({});
  });
});
