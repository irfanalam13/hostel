/**
 * Authentication user journey (Cypress).
 *
 * Mirrors the Playwright auth spec at a higher level as a second, independent
 * signal — if both frameworks agree the login flow works, regressions are real.
 */
describe("Authentication", () => {
  it("validates the Hostel ID format before calling the API", () => {
    cy.mockApi();
    cy.visit("/login");
    cy.findByLabelText("Hostel ID").type("BAD-ID");
    cy.findByLabelText(/username/i).type("warden");
    cy.findByLabelText("Password").type("secret123");
    cy.contains("button", "Sign in").click();
    cy.contains(/official Hostel ID format/i).should("be.visible");
    cy.url().should("include", "/login");
  });

  it("logs in and reaches the dashboard", () => {
    cy.login();
    cy.window().its("localStorage.session_active").should("eq", "1");
  });

  it("shows an error on bad credentials", () => {
    cy.mockApi({ unauthenticated: true });
    cy.visit("/login");
    cy.findByLabelText("Hostel ID").type("HTL-ABC12345");
    cy.findByLabelText(/username/i).type("warden");
    cy.findByLabelText("Password").type("wrong");
    cy.contains("button", "Sign in").click();
    cy.contains(/invalid credentials/i).should("be.visible");
    cy.url().should("include", "/login");
  });

  it("redirects an unauthenticated visitor away from a protected route", () => {
    cy.mockApi({ unauthenticated: true });
    cy.visit("/dashboard");
    cy.url().should("include", "/login");
  });
});
