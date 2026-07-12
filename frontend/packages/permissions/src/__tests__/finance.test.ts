import { describe, it, expect } from "vitest";
import { can } from "../permissions";
import { permissionForPath } from "../routePolicy";

describe("finance route policy", () => {
  it("gates every finance route on finance:manage", () => {
    expect(permissionForPath("/finance")).toBe("finance:manage");
    expect(permissionForPath("/finance/invoices")).toBe("finance:manage");
    expect(permissionForPath("/finance/invoices/abc-123")).toBe("finance:manage");
    expect(permissionForPath("/finance/payments")).toBe("finance:manage");
    expect(permissionForPath("/finance/reports")).toBe("finance:manage");
  });

  it("does not collide with unrelated staff routes", () => {
    // /finance must not swallow /staff or other prefixes.
    expect(permissionForPath("/staff")).toBe("staff:manage");
  });
});

describe("finance permission grants", () => {
  it("grants finance:manage to finance-capable roles", () => {
    expect(can("OWNER", "finance:manage")).toBe(true);
    expect(can("ADMIN", "finance:manage")).toBe(true);
    expect(can("MANAGER", "finance:manage")).toBe(true);
    expect(can("ACCOUNTANT", "finance:manage")).toBe(true);
  });

  it("withholds finance:manage from roles without it", () => {
    expect(can("RECEPTIONIST", "finance:manage")).toBe(false);
    expect(can("WARDEN", "finance:manage")).toBe(false);
    expect(can("STAFF", "finance:manage")).toBe(false);
    expect(can("STUDENT", "finance:manage")).toBe(false);
  });
});
