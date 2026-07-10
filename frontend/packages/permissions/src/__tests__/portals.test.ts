import { describe, it, expect } from "vitest";
import { can, portalHomeForRole } from "../permissions";
import { permissionForPath } from "../routePolicy";
import { normalizeRole } from "../roles";

describe("portal route policy (Prompt 02)", () => {
  it("maps portal routes to portal permissions", () => {
    expect(permissionForPath("/student/dashboard")).toBe("student-portal:view");
    expect(permissionForPath("/parent/dashboard")).toBe("parent-portal:view");
    // /students (staff area) must NOT collide with /student (portal).
    expect(permissionForPath("/students")).toBe("students:manage");
    expect(permissionForPath("/students/123")).toBe("students:manage");
  });

  it("grants portal access only to portal roles", () => {
    expect(can("STUDENT", "student-portal:view")).toBe(true);
    expect(can("RESIDENT", "student-portal:view")).toBe(true);
    expect(can("PARENT", "parent-portal:view")).toBe(true);
    // Staff/admin can never enter end-user portals...
    expect(can("WARDEN", "student-portal:view")).toBe(false);
    expect(can("MANAGER", "parent-portal:view")).toBe(false);
    // ...and portal roles hold no staff permissions.
    expect(can("STUDENT", "residents:manage")).toBe(false);
    expect(can("PARENT", "dashboard:view")).toBe(false);
  });

  it("owner/admin wildcard includes portal views (platform oversight)", () => {
    expect(can("OWNER", "student-portal:view")).toBe(true);
  });

  it("READ_ONLY sees dashboards/reports but manages nothing", () => {
    expect(can("READ_ONLY", "dashboard:view")).toBe(true);
    expect(can("READ_ONLY", "reports:view")).toBe(true);
    expect(can("READ_ONLY", "residents:manage")).toBe(false);
    expect(can("READ_ONLY", "settings:manage")).toBe(false);
  });

  it("routes roles to their portal home", () => {
    expect(portalHomeForRole("STUDENT")).toBe("/student/dashboard");
    expect(portalHomeForRole("RESIDENT")).toBe("/student/dashboard");
    expect(portalHomeForRole("PARENT")).toBe("/parent/dashboard");
    expect(portalHomeForRole("OWNER")).toBe("/dashboard");
    expect(portalHomeForRole("WARDEN")).toBe("/dashboard");
  });

  it("normalizes the new backend roles instead of defaulting to OWNER", () => {
    expect(normalizeRole("READ_ONLY")).toBe("READ_ONLY");
    expect(normalizeRole("read_only")).toBe("READ_ONLY");
    expect(normalizeRole("RESIDENT")).toBe("RESIDENT");
    expect(normalizeRole("ADMIN")).toBe("ADMIN");
  });
});
