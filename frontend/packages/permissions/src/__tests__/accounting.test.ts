import { describe, it, expect } from "vitest";
import { can } from "../permissions";
import { permissionForPath } from "../routePolicy";

describe("accounting route policy", () => {
  it("gates every accounting route on accounting:manage", () => {
    expect(permissionForPath("/accounting")).toBe("accounting:manage");
    expect(permissionForPath("/accounting/journals")).toBe("accounting:manage");
    expect(permissionForPath("/accounting/journals/abc-123")).toBe("accounting:manage");
    expect(permissionForPath("/accounting/statements")).toBe("accounting:manage");
    expect(permissionForPath("/accounting/setup")).toBe("accounting:manage");
  });

  it("does not collide with the finance prefix", () => {
    expect(permissionForPath("/finance")).toBe("finance:manage");
  });
});

describe("accounting permission grants", () => {
  it("grants accounting:manage to accounting-capable roles", () => {
    expect(can("OWNER", "accounting:manage")).toBe(true);
    expect(can("ADMIN", "accounting:manage")).toBe(true);
    expect(can("MANAGER", "accounting:manage")).toBe(true);
    expect(can("ACCOUNTANT", "accounting:manage")).toBe(true);
  });

  it("withholds accounting:manage from roles without it", () => {
    expect(can("RECEPTIONIST", "accounting:manage")).toBe(false);
    expect(can("WARDEN", "accounting:manage")).toBe(false);
    expect(can("STAFF", "accounting:manage")).toBe(false);
    expect(can("STUDENT", "accounting:manage")).toBe(false);
  });
});
