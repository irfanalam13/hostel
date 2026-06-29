import { describe, it, expect, beforeEach, vi } from "vitest";
import { storage } from "@/shared/lib/storage";

describe("secure storage guardrails (Phase 10)", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    vi.restoreAllMocks();
  });

  it("persists ordinary non-sensitive values", () => {
    storage.set("hostel_code", "HTL-ABC12345");
    expect(storage.get("hostel_code")).toBe("HTL-ABC12345");
  });

  it("refuses to store a JWT-shaped value", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    const jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NSJ9.s5d8fJ2kQ9aBcD1eFgHiJkLmNoPqRsTuVwXyZ012345";
    storage.set("whatever", jwt);
    expect(storage.get("whatever")).toBeNull();
  });

  it("refuses to store under a credential-looking key", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    storage.set("access_token", "abc123");
    storage.set("api_key", "xyz");
    expect(storage.get("access_token")).toBeNull();
    expect(storage.get("api_key")).toBeNull();
  });

  it("clearAll wipes both web-storage areas", () => {
    storage.set("hostel_code", "HTL-ABC12345");
    sessionStorage.setItem("draft", "x");
    storage.clearAll();
    expect(storage.get("hostel_code")).toBeNull();
    expect(sessionStorage.getItem("draft")).toBeNull();
  });
});
